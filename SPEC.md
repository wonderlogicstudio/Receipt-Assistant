# SPEC.md

# 영수증 OCR 엑셀 비서 기능 명세

## 1. 핵심 워크플로우

```text
영수증 이미지/PDF 업로드
+ 카드 사용내역 엑셀 업로드
        ↓
OCR Provider 실행
        ↓
OCR 결과 객체 생성
        ↓
Receipt Parser로 구조화
        ↓
Validator로 오류/누락/중복/카드매칭 검증
        ↓
사용자 검수
        ↓
Excel Exporter로 표준 엑셀 생성
        ↓
다운로드
```

---

## 2. 데이터 모델

## 2.1 ReceiptRecord

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| id | str | Y | 내부 고유 ID |
| session_id | str/null | N | 처리 세션 ID |
| source_file_id | str | Y | 원본 파일 ID |
| ocr_result_id | str/null | N | OCR 결과 ID |
| source_file_name | str | Y | 원본 파일명 |
| stored_relative_path | str/null | N | 내부 저장 상대 경로 |
| transaction_date | date/null | N | 사용일자 |
| merchant_name | str/null | N | 상호 |
| business_number | str/null | N | 사업자번호 |
| evidence_type | str | Y | receipt_image, receipt_pdf, ocr_text, manual |
| payment_method | str | Y | 카드, 현금, 계좌이체, 미확인 |
| supply_amount | int/null | N | 공급가액 |
| vat_amount | int/null | N | 부가세 |
| total_amount | int/null | N | 총액 |
| recommended_expense_category | str/null | N | 시스템 추천 비용항목 |
| recommended_expense_category_reason | str/null | N | 추천 근거 |
| expense_category | str/null | N | 사용자가 검수한 최종 비용항목 |
| card_match_status | str | Y | matched, candidate, unmatched, mismatch, needs_review |
| review_status | str | Y | pending, needs_review, approved, rejected, excluded |
| review_reason | str | Y | 검토 사유 텍스트 |
| review_reasons | list[str] | Y | 검토 사유 목록 |
| confidence | float/null | N | OCR 신뢰도 |
| parser_warnings | list[str] | Y | 파서 경고 목록 |
| validation_warnings | list[str] | Y | 검증 경고 목록 |
| matched_card_transaction_id | str/null | N | 매칭된 카드 사용내역 ID |
| duplicate_group_id | str/null | N | 중복 의심 그룹 ID |
| export_included | bool | Y | 엑셀 정리내역 포함 여부 |
| user_note | str/null | N | 사용자 메모 |
| created_at | datetime | Y | 생성일시 |
| ocr_provider | str/null | N | OCR provider 이름 |

---

## 2.2 CardTransaction

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| id | str | Y | 내부 고유 ID |
| session_id | str/null | N | 처리 세션 ID |
| source_file_id | str | Y | 원본 파일 ID |
| source_file_name | str | Y | 카드내역 원본 파일명 |
| stored_relative_path | str/null | N | 내부 저장 상대 경로 |
| row_number | int | Y | 원본 행 번호 |
| transaction_date | date/null | N | 카드 사용일 |
| merchant_name | str/null | N | 가맹점명 |
| total_amount | int/null | N | 사용금액 |
| card_name | str/null | N | 카드명 |
| approval_number | str/null | N | 승인번호 |
| currency | str | Y | 통화 |
| parse_status | str | Y | parsed, needs_review, failed |
| warning_messages | list[str] | Y | 파싱 경고 목록 |
| created_at | datetime | Y | 생성일시 |

---

## 2.3 OCRResult

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| id | str | Y | OCR 결과 ID |
| source_file_id | str | Y | 원본 파일 ID |
| source_file_name | str | Y | 원본 파일명 |
| stored_relative_path | str/null | N | 내부 저장 상대 경로 |
| provider | str | Y | mock, azure 등 |
| raw_text | str | Y | OCR 원문 |
| raw_json | dict/null | N | Provider 원본 응답 |
| confidence | float/null | N | 전체 신뢰도 |
| status | str | Y | completed, failed, skipped |
| error_message | str/null | N | 오류 메시지 |
| created_at | datetime | Y | 생성일시 |

---

## 3. Enum 정의

### EvidenceType

```text
receipt_image
receipt_pdf
ocr_text
manual
```

### ReviewStatus

```text
pending
needs_review
approved
rejected
excluded
```

### CardMatchStatus

```text
matched
candidate
unmatched
mismatch
needs_review
```

### RecommendedCategory

초기 기본값:

```text
식대
교통비
접대비
소모품비
통신비
광고선전비
복리후생비
기타
미분류
```

---

## 4. 검증 규칙

## 4.1 필수값 검증

| 조건 | 처리 |
|---|---|
| transaction_date 없음 | review_status = needs_review, reason = 날짜누락 |
| merchant_name 없음 | review_status = needs_review, reason = 상호누락 |
| total_amount 없음 또는 0 이하 | review_status = needs_review, reason = 금액누락 |

## 4.2 금액 검증

| 조건 | 처리 |
|---|---|
| supply_amount + vat_amount != total_amount | 금액불일치 표시 |
| vat_amount 없음 | 부가세미확인 표시 |
| supply_amount 없음, total_amount 있음 | 공급가액미확인 표시 |

주의:
부가세를 임의 추정할 수는 있지만 추정값과 OCR 추출값을 구분해야 합니다.

## 4.3 중복 검증

중복 후보 기준:

1. 거래일이 동일하거나 ±1일 이내
2. 총액이 동일
3. 상호명이 동일하거나 유사

중복은 확정하지 않고 “중복의심”으로 표시합니다.

## 4.4 카드내역 매칭

| 조건 | 상태 |
|---|---|
| 날짜 동일, 금액 동일, 상호 유사 | 매칭완료 |
| 날짜 ±1일, 금액 동일 | 후보있음 |
| 매칭 후보 없음 | 미매칭 |

---

## 5. Excel 산출물 명세

파일명:

```text
receipt_summary_YYYYMMDD_HHMMSS.xlsx
```

필수 시트:

| 시트명 | 설명 |
|---|---|
| 01_정리내역 | 최종 검수된 영수증 목록 |
| 02_월별요약 | 월별 총액, 공급가액, 부가세 합계 |
| 03_비용항목별요약 | 사용자가 검수한 최종 비용항목별 집계 |
| 04_검토필요 | 오류, 누락, 중복, 미매칭 목록 |
| 05_카드대조 | 카드 사용내역과 영수증 매칭 결과 |
| 06_원본파일목록 | 원본 파일명, 내부추적ID, 처리상태 |
| 07_처리로그 | 처리 단계, 상태, 짧은 메시지 |
| 08_제외내역 | 검수 화면에서 제외한 영수증 목록 |

## 5.1 01_정리내역 컬럼

```text
No
사용일자
상호
사업자번호
총액
공급가액
부가세
결제수단
시스템추천비용항목
최종비용항목
검수상태
검토사유
카드매칭상태
카드매칭사유
중복의심여부
원본파일명
비고
```

주의:
엑셀 파일에는 OCR 원문 전체와 Provider raw JSON 전체를 쓰지 않습니다. 개인정보 보호를 위해 처리 상태와 짧은 메시지만 `07_처리로그`에 기록합니다.

## 5.2 Excel 서식 규칙

| 항목 | 규칙 |
|---|---|
| 금액 | 천 단위 콤마, 숫자 형식 |
| 날짜 | yyyy-mm-dd |
| 헤더 | 고정 행, 굵게 |
| 검토필요 | 별도 시트 분리 |
| 합계 | 월별/항목별 합계 행 표시 |
| 원본파일명 | 파일명만 표시, 전체 로컬 경로 표시 금지 |

---

## 6. OCR Provider 인터페이스

```python
class OCRProvider:
    def extract(self, file_path: str) -> OCRResult:
        ...
```

필수 구현:

| Provider | 목적 |
|---|---|
| MockOCRProvider | 테스트와 UI 개발용 |
| AzureDocumentIntelligenceProvider | 실제 OCR API용 |

OpenAI API는 MVP 필수 의존성이 아닙니다. 나중에 애매한 건만 보정하는 LLMProvider로 분리합니다.

---

## 7. LLMProvider 확장 지점

초기에는 구현하지 않아도 됩니다.

```python
class LLMProvider:
    def normalize_receipt(self, raw_text: str) -> dict:
        ...
```

호출 조건:

1. OCR confidence가 낮은 경우
2. 필수 필드가 누락된 경우
3. 비용항목 추천이 실패한 경우
4. 사용자가 AI 보정 버튼을 누른 경우

---

## 8. 보안/개인정보 기준

1. 원본 파일 경로를 사용자에게 노출하지 않는다.
2. OCR 원문을 로그에 남기지 않는다.
3. API Key는 `.env`로 관리한다.
4. 업로드 파일은 보관 기간을 둔다.
5. 삭제 기능을 제공한다.
6. 테스트 데이터에는 실제 개인정보를 넣지 않는다.
7. 엑셀 파일에는 전체 로컬 경로를 넣지 않는다.
