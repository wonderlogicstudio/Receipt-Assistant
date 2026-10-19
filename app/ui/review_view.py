from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.classifier.merchant_candidate import MerchantCandidateMatcher
from app.core.config import get_config
from app.core.receipt_models import ReceiptRecord
from app.db.merchant_repository import MerchantRepository
from app.ui.review_utils import (
    REVIEW_FILTER_ALL,
    REVIEW_FILTER_OPTIONS,
    REVIEW_ISSUE_OPTIONS,
    build_review_issue_summary,
    filter_receipt_records_for_review,
    format_display_amount,
    map_review_status_to_label,
    merge_reviewed_records,
    resolve_receipt_source_preview,
    review_issue_labels,
)
from app.ui.summary_view import render_review_summary
from app.ui.receipt_form import AMOUNT_FIELDS, apply_receipt_form, clear_receipt_draft, render_receipt_form


def render_review_view(
    records: list[ReceiptRecord],
    *,
    merchant_address_hints: dict[str, object] | None = None,
) -> list[ReceiptRecord]:
    if not records:
        return []
    st.session_state["receipt_records"] = records
    st.session_state["reviewed_receipt_records"] = records
    render_review_summary(records)
    status_filter, issue_filters = _render_review_filters(records)
    filtered = filter_receipt_records_for_review(
        records, status_filter=status_filter, issue_filters=issue_filters,
    )
    if not filtered:
        st.info("현재 필터에 해당하는 영수증이 없습니다.")
    else:
        by_id = {record.id: record for record in filtered}
        pending = st.session_state.pop("receipt_review_pending_selection", None)
        if pending in by_id:
            st.session_state["review_selected_receipt_id"] = pending
        if st.session_state.get("review_selected_receipt_id") not in by_id:
            st.session_state["review_selected_receipt_id"] = filtered[0].id
        selected_index = list(by_id).index(st.session_state["review_selected_receipt_id"])
        overview_key = f"receipt_overview_{st.session_state.get('receipt_review_grid_revision', 0)}"
        dataframe = build_receipt_overview(filtered)
        styled = dataframe.style.format(
            {label: lambda value: format_display_amount(value, suffix="", missing="—") for _, label in AMOUNT_FIELDS},
            na_rep="—",
        )
        st.caption(f"전체 {len(records):,}건 중 {len(filtered):,}건 표시 · 금액 단위: 원 · 행을 클릭하면 상세 검수가 열립니다.")
        st.dataframe(
            styled, hide_index=True, width="stretch", height=min(440, 36 * (len(filtered) + 1) + 4), placeholder="—",
            key=overview_key, on_select=lambda: _select_overview_row(list(by_id), overview_key), selection_mode="single-cell",
            column_config={label: st.column_config.NumberColumn(label, width="small") for _, label in AMOUNT_FIELDS},
        )
        selection, action = st.columns([5, 1])
        with selection:
            selected_id = st.selectbox(
                "검수할 영수증", options=list(by_id), key="review_selected_receipt_id",
                index=selected_index,
                format_func=lambda identifier: _record_detail_label(by_id[identifier], list(by_id).index(identifier) + 1),
            )
        with action:
            st.caption("원본과 비교")
            if st.button("상세 검수 열기", type="primary"):
                st.session_state["receipt_review_dialog_ids"] = list(by_id)
                st.session_state["receipt_review_dialog_id"] = selected_id
                st.session_state["receipt_review_dialog_open"] = True
    if st.session_state.get("receipt_review_dialog_open"):
        _render_receipt_dialog(merchant_address_hints or {})
    return records


def build_receipt_overview(records: list[ReceiptRecord]) -> pd.DataFrame:
    rows = [{
        "사용일자": record.transaction_date.isoformat() if record.transaction_date else "—", "상호": record.merchant_name or "—",
        "사업자번호": record.business_number or "—",
        **{label: getattr(record, field) for field, label in AMOUNT_FIELDS},
        "결제수단": record.payment_method or "—",
        "중복의심": "Y" if record.duplicate_group_id or record.duplicate_candidate_ids or record.duplicate_reason else "—",
        "검수상태": map_review_status_to_label(record.review_status),
    } for record in records]
    dataframe = pd.DataFrame(rows, columns=[
        "사용일자", "상호", "사업자번호", "할인금액", "공급가액", "부가세", "최종결제금액", "결제수단", "중복의심", "검수상태",
    ], dtype=object)
    for _, label in AMOUNT_FIELDS:
        dataframe[label] = pd.array(dataframe[label], dtype="Int64")
    return dataframe


def _select_overview_row(identifiers: list[str], widget_key: str) -> None:
    selection = st.session_state[widget_key]["selection"]
    cells = selection.get("cells", [])
    rows = [cells[0][0]] if cells else selection.get("rows", [])
    if rows and 0 <= rows[0] < len(identifiers):
        st.session_state["review_selected_receipt_id"] = identifiers[rows[0]]
        st.session_state["receipt_review_dialog_ids"] = list(identifiers)
        st.session_state["receipt_review_dialog_id"] = identifiers[rows[0]]
        st.session_state["receipt_review_dialog_open"] = True


def _close_receipt_dialog() -> None:
    st.session_state["receipt_review_pending_selection"] = st.session_state.get("receipt_review_dialog_id")
    st.session_state["receipt_review_dialog_open"] = False
    # shortcut: rebuilding clears stale focus and sorting; persist grid state if sorting must survive closing.
    st.session_state["receipt_review_grid_revision"] = st.session_state.get("receipt_review_grid_revision", 0) + 1
    st.session_state.pop("receipt_review_form_active_id", None)


@st.dialog("상세 검수", width="large", dismissible=True, on_dismiss=_close_receipt_dialog)
def _render_receipt_dialog(merchant_address_hints: dict[str, object]) -> None:
    st.html("""<style>
    [data-testid="stDialog"] {padding:0 !important;}
    [data-testid="stDialog"] > div {width:min(1320px, calc(100vw - 32px)); max-width:calc(100vw - 32px);}
    [data-testid="stDialog"] [role="dialog"] {width:100%; max-height:calc(100dvh - 32px);}
    .st-key-receipt_review_original [data-testid="stImage"] img {
        max-height:calc(100dvh - 380px); width:auto !important; max-width:100%; object-fit:contain; margin:auto;
    }
    .st-key-receipt_review_form {max-height:clamp(160px, calc(100dvh - 310px), 900px); min-height:0; overflow:auto;}
    </style>""")
    records = st.session_state["reviewed_receipt_records"]
    by_id = {record.id: record for record in records}
    identifiers = [identifier for identifier in st.session_state["receipt_review_dialog_ids"] if identifier in by_id]
    selected_id = st.session_state.get("receipt_review_dialog_id")
    if selected_id not in identifiers:
        _close_receipt_dialog()
        st.rerun()
    index = identifiers.index(selected_id)
    selected = by_id[selected_id]
    st.caption(f"{index + 1:,} / {len(identifiers):,} · {selected.merchant_name or '상호 미확인'}")
    original, form = st.columns(2)
    with original, st.container(border=False, key="receipt_review_original"):
        _render_source_preview(selected)
    with form, st.container(border=False, key="receipt_review_form"):
        values = render_receipt_form(selected)
        _render_review_detail_panel(selected)
        _render_merchant_candidates(selected.id, values, merchant_address_hints.get(selected.id))
    st.divider()
    previous, following, _, close, save, save_next = st.columns([1, 1, 1, 1, 1, 1.7])
    previous_clicked = previous.button("이전", disabled=index == 0)
    next_clicked = following.button("다음", disabled=index == len(identifiers) - 1)
    close_clicked = close.button("닫기")
    save_clicked = save.button("저장")
    save_next_clicked = save_next.button("저장 후 다음", type="primary")
    if save_clicked or save_next_clicked:
        try:
            updated = apply_receipt_form(selected, values)
        except ValueError:
            st.error("저장하지 않았습니다. 금액을 정수와 천 단위 콤마로 확인해 주세요.")
            return
        records = merge_reviewed_records(records, [updated])
        st.session_state["receipt_records"] = records
        st.session_state["reviewed_receipt_records"] = records
        st.session_state["export_file_bytes"] = None
        st.session_state["export_file_name"] = None
        clear_receipt_draft(selected.id)
        st.toast("검수값을 저장했습니다.")
        if save_next_clicked and index < len(identifiers) - 1:
            st.session_state["receipt_review_dialog_id"] = identifiers[index + 1]
        elif save_next_clicked:
            _close_receipt_dialog()
        st.session_state["receipt_review_pending_selection"] = st.session_state["receipt_review_dialog_id"]
        st.rerun()
    if previous_clicked or next_clicked:
        st.session_state["receipt_review_dialog_id"] = identifiers[index + (1 if next_clicked else -1)]
        st.rerun()
    if close_clicked:
        _close_receipt_dialog()
        st.rerun()


def _render_review_filters(records: list[ReceiptRecord]) -> tuple[str, list[str]]:
    issue_summary = build_review_issue_summary(records)
    filter_columns = st.columns([1, 2])
    status_filter = filter_columns[0].selectbox(
        "검수상태 필터",
        options=REVIEW_FILTER_OPTIONS,
        index=REVIEW_FILTER_OPTIONS.index(REVIEW_FILTER_ALL),
        key="receipt_review_status_filter",
        format_func=lambda label: "검토필요만 보기" if label == "검토필요" else label,
    )
    issue_options = [
        f"{issue} ({issue_summary.get(issue, 0):,})"
        for issue in REVIEW_ISSUE_OPTIONS
        if issue_summary.get(issue, 0) > 0
    ]
    selected_issue_labels = filter_columns[1].multiselect(
        "검토 항목 필터",
        options=issue_options,
        key="receipt_review_issue_filter",
    )
    selected_issues = [label.split(" (", 1)[0] for label in selected_issue_labels]
    return status_filter, selected_issues


def _render_review_detail_panel(selected_record: ReceiptRecord) -> None:
    detail_rows = [
        {"항목": "파일명", "값": _safe_file_name(selected_record.source_file_name)},
        {"항목": "상호", "값": selected_record.merchant_name or "-"},
        {"항목": "거래일자", "값": selected_record.transaction_date.isoformat() if selected_record.transaction_date else "-"},
        {"항목": "사업자번호", "값": selected_record.business_number or "-"},
        {"항목": "총액", "값": format_display_amount(selected_record.total_amount)},
        {"항목": "별도 최종결제금액", "값": format_display_amount(selected_record.final_amount)},
        {"항목": "실제결제액 추출값", "값": format_display_amount(selected_record.paid_amount)},
        {"항목": "결제수단", "값": selected_record.payment_method or "-"},
        {"항목": "검토 항목", "값": "; ".join(review_issue_labels(selected_record)) or "-"},
    ]
    with st.expander("상세정보", expanded=False):
        st.table(detail_rows)


def _render_source_preview(record: ReceiptRecord | None) -> None:
    st.caption("원본 미리보기")
    if record is None:
        st.info("원본을 볼 행을 선택해 주세요.")
        return
    config = get_config()
    preview = resolve_receipt_source_preview(
        record,
        upload_root=config.upload_root,
        upload_relative_root=config.upload_relative_root,
    )
    if preview.is_image:
        started_at = time.perf_counter()
        payload = _preview_image_payload(preview.path)
        st.session_state["review_preview_elapsed_ms"] = int((time.perf_counter() - started_at) * 1000)
        st.image(payload, caption="영수증 원본", use_container_width=True)
        return
    st.info(preview.message or "원본 미리보기를 사용할 수 없습니다.")


def _record_detail_label(record: ReceiptRecord, index: int) -> str:
    merchant = record.merchant_name or "상호 미확인"
    amount = format_display_amount(record.total_amount, missing="금액 미확인")
    date = record.transaction_date.isoformat() if record.transaction_date else "날짜 미확인"
    return f"{index}. {date} | {merchant} | {amount}"


def _safe_file_name(value: str | None) -> str:
    if not value:
        return "파일명 없음"
    return Path(str(value).replace("\\", "/")).name or "파일명 없음"


def _apply_merchant_candidate(receipt_id: str, name: str) -> None:
    st.session_state['receipt_review_drafts'][receipt_id]['merchant_name'] = name
    st.session_state[f'receipt_input_{receipt_id}_merchant_name'] = name


def _render_merchant_candidates(receipt_id: str, values: dict[str, Any], address_hint) -> None:
    key = 'merchant_search_result_' + receipt_id
    query = (values.get('merchant_name'), values.get('business_number'))
    if st.button('상호 찾기', key='merchant_search_' + receipt_id):
        st.session_state.pop('merchant_candidate_choice_' + receipt_id, None)
        matcher = _build_merchant_matcher()
        candidates = matcher.find_candidates(merchant_name=query[0], business_number=query[1],
                                             address_hint=address_hint) if matcher else []
        st.session_state[key] = (query, candidates[:5])
    stored_query, candidates = st.session_state.get(key, (None, []))
    if stored_query != query:
        return
    if not candidates:
        st.info('사업자번호 또는 상호·주소에 맞는 등록 후보가 없습니다. 원본을 확인해 입력해 주세요.')
        return
    st.caption('DB 조회 후보 · 원본과 비교해 선택하세요. 입력란에 적용한 뒤 저장해야 표와 엑셀에 반영됩니다.')
    def description(index):
        candidate = candidates[index]
        match = '사업자번호 일치' if candidate.match_type == 'business_number_exact' else '상호·주소 유사 후보'
        source = '사용자 검수 사전' if candidate.source in {'review', 'user_review'} else '등록 상호 사전'
        return f'{candidate.candidate_merchant_name} · {match} · {source}'
    choice = st.selectbox('DB 조회 후보', range(len(candidates)), index=None, format_func=description,
                          placeholder='후보를 선택하세요', key='merchant_candidate_choice_' + receipt_id)
    if choice is not None:
        st.button('선택 상호를 입력란에 적용', key='merchant_candidate_apply_' + receipt_id,
                  on_click=_apply_merchant_candidate,
                  args=(receipt_id, candidates[choice].candidate_merchant_name))


def _build_merchant_matcher() -> MerchantCandidateMatcher | None:
    try:
        config = get_config()
        lookup_path = config.merchant_lookup_db_path
        repository = MerchantRepository(config=config, db_path=lookup_path, read_only=lookup_path is not None)
        cache = st.session_state.setdefault("merchant_candidate_cache", {})
        if not isinstance(cache, dict):
            cache = {}
            st.session_state["merchant_candidate_cache"] = cache
        metrics = st.session_state.setdefault("review_performance_summary", {})
        if not isinstance(metrics, dict):
            metrics = {}
            st.session_state["review_performance_summary"] = metrics
        return _SessionCachedMerchantMatcher(MerchantCandidateMatcher(repository), cache, metrics)
    except Exception:
        return None


class _SessionCachedMerchantMatcher:
    def __init__(
        self,
        matcher: MerchantCandidateMatcher,
        cache: dict[tuple[str, str, str], list[Any]],
        metrics: dict[str, object] | None = None,
    ) -> None:
        self.matcher = matcher
        self.cache = cache
        self.metrics = metrics

    def find_candidates(
        self,
        *,
        merchant_name: object = None,
        business_number: object = None,
        address_hint: object = None,
    ) -> list[Any]:
        key = (_cache_text(merchant_name), _cache_text(business_number), _cache_text(address_hint))
        started_at = time.perf_counter()
        if key in self.cache:
            _increment_review_metric(self.metrics, "candidate_cache_hit_count")
            result = self.cache[key]
        else:
            _increment_review_metric(self.metrics, "candidate_cache_miss_count")
            result = self.matcher.find_candidates(
                merchant_name=merchant_name,
                business_number=business_number,
                address_hint=address_hint,
            )
            self.cache[key] = result
        _increment_review_metric(self.metrics, "candidate_lookup_count")
        _increment_review_metric(
            self.metrics,
            "candidate_lookup_elapsed_ms",
            int((time.perf_counter() - started_at) * 1000),
        )
        return result


def _increment_review_metric(metrics: dict[str, object] | None, key: str, value: int = 1) -> None:
    if metrics is None:
        return
    try:
        metrics[key] = int(metrics.get(key, 0) or 0) + int(value)
    except Exception:
        metrics[key] = int(value)


def _cache_text(value: object) -> str:
    if isinstance(value, dict):
        return "|".join(f"{key}={value.get(key) or ''}" for key in sorted(value))
    return str(value or "")


def _preview_image_payload(path: Path | None) -> object:
    if path is None:
        return ""
    try:
        from PIL import Image, ImageOps

        image = Image.open(path)
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1400, 1400))
        return image.copy()
    except Exception:
        return ""
