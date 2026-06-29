# DECISIONS.md

# Architecture and Product Decisions

이 문서는 개발 중 방향 변경과 주요 결정을 기록합니다.

---

## ADR-001: 첫 MVP는 웹 도구로 시작한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-06 |
| 결정 | 네이티브 모바일 앱이 아니라 Streamlit 기반 웹 MVP로 시작한다 |
| 이유 | 업로드→OCR→검수→엑셀 다운로드 흐름을 가장 빠르게 검증하기 위해서 |
| 영향 | 모바일은 5주차 이후 PWA/반응형 웹으로 검토 |
| 리스크 | 모바일 촬영 업로드 경험은 초기에는 부족할 수 있음 |
| 대응 | 웹 MVP 검증 후 모바일 업로드 화면을 별도 개선 |

---

## ADR-002: OpenAI API는 MVP 필수 의존성으로 두지 않는다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-06 |
| 결정 | 기본 플로우는 OCR API + 규칙 기반 검증 + 엑셀 산출물로 구성한다 |
| 이유 | 비용, 개인정보, 장애 포인트를 줄이기 위해서 |
| 영향 | LLMProvider 인터페이스만 확장 지점으로 둔다 |
| 리스크 | 애매한 영수증 해석 품질이 낮을 수 있음 |
| 대응 | 1.5차에서 애매한 건만 OpenAI API 보정 옵션 추가 |

---

## ADR-003: 제품의 핵심 산출물은 엑셀 파일이다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-06 |
| 결정 | OCR 화면보다 표준 엑셀 산출물 품질을 우선한다 |
| 이유 | 고객이 돈을 내는 결과물은 세무사 전달용 정리 파일이기 때문 |
| 영향 | Excel exporter와 검수 상태 관리에 테스트를 집중 |
| 리스크 | UI가 초기에는 단순할 수 있음 |
| 대응 | 파일럿에서 실제 엑셀 양식 피드백을 받아 개선 |

---

## ADR-004: 세무 판단 표현을 금지한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-06 |
| 결정 | 전문가 판단 영역으로 오인될 수 있는 표현을 사용하지 않는다 |
| 이유 | 증빙 정리 보조 도구의 역할을 명확히 하기 위해서 |
| 영향 | UI와 엑셀 컬럼은 추천/검토/확인 중심으로 설계 |
| 리스크 | 고객이 자동화 수준을 낮게 느낄 수 있음 |
| 대응 | “세무사 전달용 표준 엑셀 정리”로 포지셔닝 |

---

## ADR-005: 파일 cleanup은 수동 dry-run 우선으로 제공한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | 업로드 원본 파일과 엑셀 출력 파일 cleanup은 자동 실행하지 않고 수동 함수로 제공하며 기본값은 dry_run으로 둔다 |
| 이유 | 원본 파일에는 개인정보가 포함될 수 있고, 운영자가 삭제 대상 규모를 먼저 확인한 뒤 명시적으로 삭제해야 하기 때문 |
| 영향 | `UPLOAD_RETENTION_DAYS`, `OUTPUT_RETENTION_DAYS`, `CLEANUP_DRY_RUN_DEFAULT` 설정을 추가한다 |
| 리스크 | 운영자가 수동 cleanup을 잊으면 보관 기간 초과 파일이 남을 수 있음 |
| 대응 | README와 CHECKLIST에 수동 cleanup 정책을 명시하고, 나중에 UI 버튼이나 운영 절차로 연결한다 |

---

## ADR-006: 파일럿 전 신규 기능보다 문서와 검증 정리를 우선한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | MVP 파일럿 전에는 신규 기능 추가보다 실행 방법, 사용자 흐름, 체크리스트, 인터뷰 질문 정리를 우선한다 |
| 이유 | 실제 사용자 테스트에서 혼선을 줄이고 현재 구현된 흐름의 가치를 검증하기 위해서 |
| 영향 | 기본 데모는 `OCR_PROVIDER=mock` 기준으로 유지하고, 실제 OCR Provider는 선택 옵션으로 둔다 |
| 리스크 | 기능 확장보다 문서 정리에 시간이 쓰인다 |
| 대응 | 파일럿 피드백을 기준으로 다음 개발 우선순위를 정한다 |

---

## ADR-007: 구현 기준으로 문서 모델과 산출물 명세를 동기화한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | README, PLAN, SPEC, CHECKLIST, AGENTS, CHANGE_CONTROL을 현재 구현 상태 기준으로 정리한다 |
| 이유 | 파일럿 전 문서와 코드의 불일치를 줄여 테스트 진행자의 혼선을 줄이기 위해서 |
| 영향 | `recommended_expense_category`와 `expense_category`의 역할을 구분하고, OCR 원문 전체와 raw JSON 전체는 엑셀 산출물에 쓰지 않는 원칙을 명확히 한다 |
| 리스크 | 문서가 구현 상태에 맞춰지면서 향후 아이디어와 현재 기능이 분리되어 보일 수 있음 |
| 대응 | 미완료 기능은 PLAN.md의 향후 항목으로 분리하고, 범위 변경은 CHANGE_CONTROL.md 절차를 따른다 |

---

## ADR-008: OCR 실패 디버그 정보는 비민감 상태 코드로만 표시한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | OCR 실패 원인을 확인할 때 원문, raw JSON, 전체 경로를 노출하지 않고 `status`, `provider`, `diagnostic_code`만 표시한다 |
| 이유 | 실제 OCR provider 사용 중 네트워크/프록시/응답 상태 문제와 파서 검수 로직을 구분하기 위해서 |
| 영향 | Streamlit 경고에는 비민감 진단 문자열만 추가되고, OCR 원문과 개인정보성 데이터는 계속 숨긴다 |
| 리스크 | 상세 원인 분석에는 여전히 터미널 또는 provider별 제한된 상태 확인이 필요할 수 있다 |
| 대안 | 전체 오류 메시지나 raw 응답 출력은 개인정보 노출 가능성이 있어 선택하지 않는다 |

---

## ADR-009: Azure OCR polling은 Retry-After와 제한 재시도를 따른다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | Azure OCR 결과 조회 시 `Retry-After` 헤더를 우선 따르고, 429/5xx 계열 HTTP 오류는 제한된 횟수만 재시도한다 |
| 이유 | 여러 영수증을 연속 처리할 때 너무 빠른 polling으로 Azure가 일시적 HTTP 오류를 반환할 수 있기 때문이다 |
| 영향 | `analyze_http_429`, `poll_http_503`처럼 비민감 status code 기반 reason을 남겨 원인을 구분한다 |
| 리스크 | Azure 서비스 상태나 계정 제한에 따른 실패는 재시도 후에도 발생할 수 있다 |
| 대안 | 무제한 재시도나 원본 응답 출력은 지연/개인정보 노출 위험이 있어 선택하지 않는다 |

---

## ADR-010: 처리 이력은 SQLite에 비민감 요약 데이터만 저장한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | MVP 처리 이력 저장은 로컬 SQLite(`data/app.db`)로 시작하고, DB에는 OCR 원문 전체, raw JSON 전체, 카드 원문 전체, 전체 로컬 경로를 저장하지 않는다 |
| 이유 | 파일럿 단계에서 과거 처리 결과를 다시 조회할 기반은 필요하지만 로그인/클라우드 DB는 아직 범위 밖이기 때문이다 |
| 영향 | Excel 파일은 DB가 아니라 파일 시스템에 저장하고 DB에는 상대경로와 요약 정보만 저장한다 |
| 리스크 | 사용자/권한 모델이 없으므로 다중 사용자 운영에는 별도 설계가 필요하다 |
| 대안 | PostgreSQL/Supabase 및 migration framework는 MVP 이후로 미룬다 |

---

## ADR-011: 처리 이력 화면은 목록 조회부터 제공한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | 5주차-B에서는 Streamlit에 `새 작업`/`처리 이력` 메뉴를 추가하고, 처리 이력은 최근 작업 목록 조회까지만 제공한다 |
| 이유 | 파일럿 전 과거 처리 결과를 확인할 필요는 있지만 재다운로드, 상세 수정, 재검수는 별도 단계로 분리하는 편이 안정적이기 때문이다 |
| 영향 | 기존 업로드, 검수, 엑셀 다운로드 화면은 `새 작업` 메뉴에서 유지한다 |
| 리스크 | 현재 새 작업 결과를 DB에 자동 저장하는 연결은 별도 단계가 필요할 수 있다 |
| 대안 | 상세 조회와 재다운로드를 한 번에 구현하는 방식은 MVP 흐름 변경 폭이 커서 선택하지 않는다 |

---

## ADR-012: 처리 이력 상세는 읽기 전용과 기존 파일 재다운로드로 제한한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | 처리 이력 상세 화면은 job 요약, 영수증/카드내역 요약, export 파일 목록과 기존 엑셀 파일 재다운로드만 제공한다 |
| 이유 | 과거 작업 재검수나 엑셀 재생성은 기존 새 작업 흐름과 데이터 정합성에 영향을 줄 수 있어 별도 단계로 분리한다 |
| 영향 | 다운로드 대상 파일은 `OUTPUT_DIR` 하위로 제한하고, 화면에는 상대경로와 전체 로컬 경로를 표시하지 않는다 |
| 리스크 | export 파일이 삭제된 경우 재다운로드는 불가하며 재생성 기능은 후속 작업이 필요하다 |
| 대안 | 상세 수정/재검수를 함께 제공하는 방식은 MVP 안정화 범위를 벗어나 선택하지 않는다 |

---

## ADR-013: 설정 화면은 읽기 전용 상태 점검 화면으로 제한한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | Streamlit 설정 화면은 현재 OCR 설정, 보관기간, 저장소/DB 상태, cleanup dry-run 결과를 안전하게 확인하는 읽기 전용 화면으로 제공한다 |
| 이유 | 파일럿 단계에서는 운영 상태 확인이 필요하지만 Provider 변경, API key 입력, 실제 삭제, DB 초기화는 오작동과 민감정보 노출 위험이 크다 |
| 영향 | 메뉴에 `설정`을 추가하되 기존 새 작업과 처리 이력 흐름은 유지하고, 화면에는 전체 로컬 경로와 key/endpoint 전체 값을 표시하지 않는다 |
| 리스크 | 실제 설정 변경이나 삭제가 필요할 때는 코드/환경변수 또는 후속 관리자 기능이 별도로 필요하다 |
| 대안 | 설정 변경 UI와 실제 cleanup 버튼을 함께 제공하는 방식은 MVP 안전 범위를 넘어 이번 단계에서 제외한다 |

---

## ADR-014: 파일럿 전에는 기능 추가보다 통합 점검과 문서 동기화를 우선한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-10 |
| 결정 | 5주차-E에서는 신규 기능을 추가하지 않고, 새 작업/처리 이력/설정 흐름의 연결 확인과 문서 최신화를 우선한다 |
| 이유 | 파일럿 전에는 구현 범위를 넓히는 것보다 현재 MVP가 실제 사용자 테스트에서 혼선 없이 실행되는지가 더 중요하다 |
| 영향 | README, PLAN, SPEC, CHECKLIST, CHANGE_CONTROL, pilot docs를 현재 구현 기준으로 정리한다 |
| 리스크 | 일부 코드 상수의 표시 문자열 개선은 별도 안정화 작업으로 남을 수 있다 |
| 대안 | 파일럿 직전 기능 추가는 회귀 위험이 있어 선택하지 않는다 |

---

## ADR-015: 할인 금액과 최종 결제금액을 분리한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-12 |
| 결정 | 할인금액이 있는 영수증은 할인 전 금액, 할인/차감 금액, 할인 적용 후 결제대상금액, 실제 결제금액을 분리해 저장하고 표시한다 |
| 이유 | 할인 후 결제금액이 0원인 경우에도 총매출액과 비용 기준 최종 결제금액을 구분해 사용자가 검수할 수 있어야 하기 때문이다 |
| 영향 | `total_amount`는 비용 기준 최종 결제금액으로 유지하고, 할인 후 0원 결제는 자동 제외하지 않고 검토필요 사유로 남긴다 |
| 리스크 | 부가세 추정값이나 결제증빙 미확인 분류와 혼동될 수 있다 |
| 대응 | 부가세 추정값 분리, 민감문구 필터링, 결제증빙 없는 영수증 자동분류는 후속 작업으로 분리한다 |

---

## ADR-016: 명시 부가세와 참고 추정값을 분리한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-12 |
| 결정 | 부가세가 명시되지 않은 영수증은 `vat_amount`에 추정값을 넣지 않고, 참고용 추정 공급가액과 참고용 추정 부가세를 별도 필드로 저장한다 |
| 이유 | 명시된 증빙 값과 검수 보조용 계산값을 구분해 사용자가 확인할 수 있어야 하기 때문이다 |
| 영향 | 엑셀 정리내역과 처리 이력 상세에는 명시 공급가액/부가세와 참고 추정값, 부가세 출처, 검토 사유가 분리되어 표시된다 |
| 리스크 | 추정값을 명시값으로 오해할 수 있다 |
| 대응 | 컬럼명과 `vat_source`, `vat_warnings`로 참고 추정값임을 드러내고, 민감문구 필터링은 후속 작업으로 분리한다 |

---

## ADR-017: OCR 민감문구는 실제 값 대신 category만 저장한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-12 |
| 결정 | OCR 결과에서 WiFi PW, 비밀번호, 카드번호 전체 등 민감문구 가능성을 감지하되 실제 민감값은 저장하거나 표시하지 않고 category와 검토 사유만 저장한다 |
| 이유 | 영수증 이미지에는 매장 안내문이나 화면 오버레이가 함께 인식될 수 있어 원문 노출을 줄여야 하기 때문이다 |
| 영향 | 검수 화면, 엑셀 정리내역, 처리 이력 상세에는 민감문구 감지 여부와 유형만 표시된다 |
| 리스크 | 사업자등록번호나 승인번호처럼 업무상 필요한 번호와 과도하게 충돌할 수 있다 |
| 대응 | 사업자등록번호와 승인번호는 이번 단계에서 무조건 제거하지 않고, 민감문구 필터는 할인금액 로직과 부가세 참고 추정 로직을 침해하지 않도록 제한한다 |

---

## ADR-018: Azure OCR Parser 입력은 제한된 context line으로 구성한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-13 |
| 결정 | Azure OCR 결과에서 전체 원문을 넘기지 않고, Parser에 필요한 금액/상호/사업자번호/전화/TEL 관련 context line만 제한적으로 전달한다 |
| 이유 | 실제 OCR 결과에는 민감문구와 화면 오버레이가 섞일 수 있지만, 할인금액·결제대상금액·카드결제금액·사업자번호 같은 업무상 필요한 라인은 Parser가 확인해야 하기 때문이다 |
| 영향 | `raw_text`는 전체 OCR 원문이 아니라 provider 요약과 제한된 context line으로 구성되며, WiFi PW, 비밀번호, token, secret, 카드번호 전체, 주민번호 형식은 민감문구 필터 대상이다 |
| 리스크 | context keyword가 부족하면 일부 영수증의 금액 또는 식별 라인이 누락될 수 있다 |
| 대응 | 실제 OCR 테스트에서 누락된 라인은 민감정보 원문을 노출하지 않는 더미 raw_text/raw_json 테스트로 보강한다 |

---

## ADR-019: 수량, 승인번호, 푸터 숫자는 금액 후보에서 보수적으로 제외한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-13 |
| 결정 | 수량 숫자, 카드/승인번호 계열의 긴 숫자, `결제금액 기준` 같은 설명 라벨 뒤의 푸터 숫자는 할인금액이나 실제결제금액 후보에서 제외한다 |
| 이유 | 실제 영수증 OCR에서 수량 1, 승인번호, 캐셔 코드 같은 숫자가 금액 컬럼으로 잘못 들어오는 사례가 반복되었기 때문이다 |
| 영향 | 명확한 최종결제금액 또는 결제대상금액이 있으면 신뢰 낮은 `paid_amount` 후보보다 해당 금액을 비용 기준 금액으로 사용한다 |
| 리스크 | 일부 특수 결제 구조에서는 실제 결제금액 후보가 검토필요로 남을 수 있다 |
| 대응 | 의심 후보는 자동 확정하지 않고 `amount_warnings`와 검토 사유로 사용자 확인이 가능하게 둔다 |

---

## ADR-020: OCR Provider 독립성을 위해 StandardOCRResult를 도입한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | 모든 OCR Provider는 provider raw response를 `StandardOCRResult`로 변환한 뒤 Parser에 전달한다 |
| 이유 | Azure 비용 의존도를 줄이고 PaddleOCR, Tesseract, 모바일 OCR, Local Runtime으로 확장하기 위해서다 |
| 영향 | `ReceiptParser`, `ReceiptValidator`, `CategoryRules`, `CardMatcher`, `ExcelExporter`는 provider별 원본 구조를 알지 않는다 |
| 리스크 | `StandardOCRResult` 설계가 부실하면 provider별 특징을 잃거나 Parser 품질이 떨어질 수 있다 |
| 대응 | Golden Test Fixture와 provider별 Adapter 테스트를 만든다 |

---

## ADR-021: Azure는 제거하지 않고 fallback 또는 유료 재처리 옵션으로 유지한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | Azure OCR은 제거하지 않고 고정확도 fallback 또는 유료 재처리 옵션으로 유지한다 |
| 이유 | Azure 품질은 괜찮지만 모든 처리를 Azure에 고정하면 비용 의존도가 커진다 |
| 영향 | 기본 처리 엔진은 향후 Local OCR로 전환할 수 있지만 Azure Adapter는 유지한다 |
| 리스크 | Provider 선택 정책이 복잡해질 수 있다 |
| 대응 | 초기에는 설정/문서 기준으로만 정의하고, provider 변경 UI는 별도 단계에서 검토한다 |

---

## ADR-022: PC Local OCR Runtime은 PaddleOCR을 1차 후보로 검토한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | PC Local OCR Runtime의 1차 후보는 PaddleOCR로 둔다 |
| 이유 | 장기적으로 OCR 비용을 줄이고 로컬 처리 가능성을 검토하기 위해서다 |
| 영향 | 웹은 OCR 엔진이 아니라 업로드/검수 화면 역할에 집중할 수 있다 |
| 리스크 | 사용자 PC 환경, 설치 난이도, 성능 편차가 발생할 수 있다 |
| 대응 | 9~11주차에서 PoC와 설치형 구조를 분리해 검토한다 |

---

## ADR-024: Azure OCR 결과는 Azure Adapter를 통해 StandardOCRResult로 정규화한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | Azure raw response는 Parser에 직접 전달하지 않고 `AzureStandardOCRAdapter`를 통해 `StandardOCRResult`로 변환한다 |
| 이유 | Parser가 Azure 전용 raw 구조에 의존하면 PaddleOCR, Tesseract, 모바일 OCR, Local Runtime 확장이 어려워지기 때문이다 |
| 영향 | Azure 구조화 필드는 `provider_fields`와 `StandardOCRTextBlock`, `StandardOCRKeyValueCandidate`, `StandardOCRTableCandidate`로 제한적으로 매핑한다 |
| 리스크 | Azure 고유 정보가 과도하게 제거되면 Parser 품질이 떨어질 수 있다 |
| 대응 | `provider_fields`에는 비민감 요약 정보만 담고, 필요한 후보값은 `key_value_candidates`와 `text_blocks`로 정규화한다. Golden fixture와 adapter 테스트로 품질을 확인한다 |

---

## ADR-025: provider_fields는 raw JSON 저장소가 아니라 비민감 provider metadata 영역으로 제한한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | `provider_fields`에는 provider별 비민감 metadata와 구조화 요약만 저장한다 |
| 이유 | `provider_fields`가 raw JSON 우회 저장소가 되면 보안 원칙과 Parser 독립성이 깨진다 |
| 영향 | `raw_response`, `raw_json`, `provider_raw_response`, `full_ocr_text`, headers, endpoint 전체 URL, `operation_location` 전체 URL은 `provider_fields`에 넣지 않는다 |
| 리스크 | 디버깅 정보가 부족할 수 있다 |
| 대응 | `diagnostic_code`, `warnings`, `adapter_version`, `page_count`, `has_tables`, `normalized_candidate_count` 같은 제한된 진단 정보만 사용한다 |

---

## ADR-026: Azure Provider 변경과 Parser 전환은 분리한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | Azure Adapter 구현, Azure Provider 연결, Parser 전환은 각각 별도 단계로 진행한다 |
| 이유 | 기존 MVP 흐름과 Azure OCR 동작을 보호하기 위해서다 |
| 영향 | 7주차-B에서는 Adapter만 구현하고, 7주차-C에서 기존 Provider와 연결을 검토하며, 8주차에서 Parser 전환을 다룬다 |
| 리스크 | 전환 단계가 늘어나 일정이 길어질 수 있다 |
| 대응 | 각 단계마다 fixture와 회귀 테스트를 추가해 안정성을 우선한다 |

---

## ADR-027: ReceiptParser 입력은 StandardOCRParserContext 기준으로 단계 전환한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | `ReceiptParser`는 Provider raw response를 직접 받지 않고, `StandardOCRParserContext` 또는 `StandardOCRResult` 기반 입력으로 단계 전환한다 |
| 이유 | Azure, PaddleOCR, Tesseract, Android ML Kit, iOS Apple Vision 등 Provider 확장 시 Parser가 provider별 원본 구조에 종속되지 않도록 하기 위해서다 |
| 영향 | 기존 raw_text Parser 경로는 즉시 삭제하지 않고 compatibility wrapper로 유지한다. 새 Parser entry는 기존 `ReceiptRecord`를 반환해야 한다 |
| 리스크 | 전환 중 기존 Parser 결과와 새 Parser 결과가 달라질 수 있다 |
| 대응 | mock, azure-like, Azure Adapter output, edge-case fixture 기반 비교 테스트를 추가하고, 기존 end-to-end export flow 테스트를 유지한다 |

---

## ADR-028: Parser 전환 중 ReceiptRecord와 ExcelExporter 구조는 유지한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | Parser 입력을 표준화하더라도 `ReceiptRecord`와 `ExcelExporter` 구조는 대규모로 변경하지 않는다 |
| 이유 | 검수 UI, 처리 이력, 엑셀 산출물이 이미 기존 `ReceiptRecord` 구조에 의존하기 때문이다 |
| 영향 | Parser 전환은 입력 계층 중심으로 진행하고, 출력 모델과 산출물은 기존 호환성을 우선한다 |
| 리스크 | 일부 `StandardOCRResult` 정보가 `ReceiptRecord`에 바로 반영되지 않을 수 있다 |
| 대응 | 필요한 정보는 `parser_warnings`, `validation_warnings`, `amount_warnings`, `vat_warnings`, `sensitive_categories` 등 기존 필드를 우선 활용한다 |

---

## ADR-029: Parser 전환은 B/C/D 단계로 분리해 회귀 위험을 줄인다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-14 |
| 결정 | Parser entry 추가, fixture 비교 테스트, Validator/Exporter 회귀 점검을 별도 단계로 분리한다 |
| 이유 | Parser는 OCR 이후 전체 흐름의 핵심이므로 한 번에 변경하면 회귀 위험이 크다 |
| 영향 | 8주차-B에서는 entry만 추가하고, 8주차-C에서 fixture 결과 비교, 8주차-D에서 downstream 회귀를 검증한다 |
| 리스크 | 단계가 늘어나 일정이 길어질 수 있다 |
| 대응 | 각 단계별 완료 기준과 rollback 기준을 명확히 둔다 |

---

## ADR-030: PaddleOCR is the first PC Local OCR Runtime candidate

| Item | Content |
|---|---|
| Date | 2026-05-15 |
| Decision | Treat PaddleOCR as the first candidate for the PC Local OCR Runtime PoC. |
| Reason | The project needs a local OCR path to reduce long-term Azure cost dependency and test whether users' PCs or office machines can process receipt images locally. |
| Impact | Week 9 focuses on an image-first Local Provider PoC. PDF handling, desktop packaging, and server runtime packaging remain follow-up work. |
| Risk | User PC OS, Python version, PaddleOCR installation status, model availability, and performance can vary significantly. |
| Response | Treat `paddleocr` as an optional dependency. Do not call actual PaddleOCR in default pytest. Put actual OCR smoke tests behind an explicit opt-in flag. |

---

## ADR-031: PaddleOCRProvider must return StandardOCRResult

| Item | Content |
|---|---|
| Date | 2026-05-15 |
| Decision | `PaddleOCRProvider` must convert PaddleOCR raw output to `StandardOCRResult` before parser use. |
| Reason | Parser and downstream services must stay independent of provider raw structures. |
| Impact | PaddleOCR raw output is normalized by `PaddleStandardOCRAdapter` into `StandardOCRTextBlock`, `key_value_candidates`, warnings, confidence, bbox, and limited non-sensitive `provider_fields`. |
| Risk | Some PaddleOCR-specific details may not fit the standard schema directly. |
| Response | Preserve only parser-relevant safe fields and non-sensitive count/flag metadata. Use Golden Fixture comparison and later quality comparison to identify gaps. |

---

## ADR-032: Actual PaddleOCR execution tests are opt-in

| Item | Content |
|---|---|
| Date | 2026-05-15 |
| Decision | Actual PaddleOCR OCR execution tests are excluded from default pytest and run only with an explicit opt-in condition such as `RUN_PADDLEOCR_TESTS=1`. |
| Reason | PaddleOCR may be missing, slow to initialize, require model files, or behave differently by OS and hardware. |
| Impact | Default pytest must pass without PaddleOCR installed. Week 9-D smoke tests are separate from normal regression tests. |
| Risk | Default tests cannot prove real OCR quality. |
| Response | Use sanitized PaddleOCR-like fixture tests for default coverage, then run opt-in image smoke tests and 10주차 Azure vs PaddleOCR quality comparison separately. |

---

## ADR-033: PaddleOCR PDF handling is deferred after the image PoC

| Item | Content |
|---|---|
| Date | 2026-05-15 |
| Decision | Week 9 PaddleOCR PoC is limited to image files. PDF handling is deferred. |
| Reason | PDF local OCR requires page rendering, multi-page handling, file-size controls, additional dependencies, and performance decisions. |
| Impact | Week 9-B/C/D focus on JPG/JPEG/PNG-style image inputs. PDF input is documented as unsupported or deferred for the local PaddleOCR path. |
| Risk | PDF receipt users do not benefit from the initial PaddleOCR PoC. |
| Response | Keep existing Azure/mock flow and later evaluate PDF local OCR in Local Runtime or a separate follow-up task. |

---

## ADR-034: Azure vs PaddleOCR 품질 비교는 표준 계층 결과만 비교한다

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-05-16 |
| 결정 | Azure와 PaddleOCR 품질 비교는 `StandardOCRResult`, `StandardOCRParserContext`, 기존 `ReceiptRecord` 핵심 필드만 사용한다. |
| 이유 | Provider raw output을 비교 기준으로 삼으면 Parser 독립성과 보안 원칙이 깨지고, Azure와 PaddleOCR 결과를 같은 제품 흐름에서 판단하기 어렵다. |
| 영향 | 10주차-B/C/D의 미리보기, side-by-side 리포트, 통계 요약, fallback 기준은 표준 계층의 비민감 요약 필드와 검토 필요 신호만 사용한다. expected fixture도 provider raw output이 아니라 안전한 sample id와 `ReceiptRecord` 핵심 필드 기준선으로 둔다. |
| 리스크 | Provider별 원본 세부 정보가 부족해 원인 분석이 제한될 수 있다. |
| 대응 | `diagnostic_code`, `warnings`, candidate count, review hint count, field match score, 처리시간 같은 비민감 지표를 남기고, 실제 raw output 분석은 별도 안전 절차로 분리한다. |

---

## ADR-035: Safe OCR preview uses StandardOCRResult text blocks only

| Item | Content |
|---|---|
| Date | 2026-05-16 |
| Decision | The Week 10-B OCR preview is built from `StandardOCRResult.text_blocks` and exposes only limited safe rows plus summary counts. |
| Reason | Reviewers need to see what PaddleOCR read without exposing provider raw output, full OCR raw text, raw JSON, full local paths, or secrets. |
| Impact | PaddleOCR smoke-test results can show safe preview rows in Settings, and Azure adapter output can reuse the same utility through `StandardOCRResult`. |
| Risk | A short preview may hide useful context for deeper quality diagnosis. |
| Response | Keep full side-by-side quality comparison, statistics, and fallback criteria in 10-C/D while preserving the no-raw-output boundary. |

---

## ADR Template

```text
## ADR-XXX: 제목

| 항목 | 내용 |
|---|---|
| 날짜 | YYYY-MM-DD |
| 결정 |  |
| 이유 |  |
| 영향 |  |
| 리스크 |  |
| 대응 |  |
```
## ADR-036: Side-by-side comparison report uses only standard and parser results

Status: Accepted

Decision:
Azure vs PaddleOCR side-by-side reports compare only `StandardOCRResult`, `StandardOCRParserContext`, and `ReceiptParser.parse_standard_context()` output. The report does not copy provider raw output, provider raw JSON, full OCR text, full file paths, Azure operation URLs, endpoints, or secrets into report rows.

Reason:
This keeps provider replacement, parser migration, and privacy boundaries intact while still allowing the team to inspect quality differences between Azure and PaddleOCR. It also preserves Week 10-D as an aggregation and fallback-policy step instead of mixing policy decisions into the first per-sample report.

Impact:
Week 10-C can show provider metrics, parsed core fields, and field equality flags per sample. Week 10-D may aggregate those safe values into summary statistics and fallback criteria, but any future policy must continue to avoid provider raw payloads.

---

## ADR-037: Provider failure details use sanitized diagnostic categories

Status: Accepted

Decision:
Provider failures may include a `diagnostic_detail_code` only when the value is a sanitized category, such as `quota_or_rate_limit`, `credential_or_permission`, `region_or_endpoint`, `non_json_error`, `runtime_error`, or `value_error`.

Reason:
The comparison UI needs enough information to distinguish external service limits from OCR quality failures, but it must not expose raw provider messages, Azure endpoint URLs, operation URLs, request IDs, keys, full local paths, raw tracebacks, or provider payloads.

Impact:
Azure HTTP 403 can be shown as `analyze_http_403` with detail `quota_or_rate_limit`. Week 10-D can aggregate these safe detail codes as environment/service availability signals. The rule applies to future providers as well: detail codes are categories, not raw errors.

---

## ADR-038: PaddleOCR line-derived candidates stay conservative

Status: Accepted

Decision:
PaddleOCRProvider may derive candidates from safe OCR lines only for obvious dates, business numbers, payment methods, and clearly labeled amounts. It must not guess merchant names from arbitrary top lines or infer total amounts from unlabeled maximum amounts.

Reason:
Early 10-sample testing showed that aggressive candidate guesses can increase apparent field presence while lowering comparison quality by turning missing fields into wrong fields.

Impact:
PaddleOCR comparisons remain more honest: missing or weak fields stay visible as review/fallback signals. Future improvements should be driven by expected fixtures and Week 10-D statistics rather than broad heuristics.

2026-05-17 update:
Explicit merchant labels such as `상호`, `상호명`, `매장명`, `가맹점명`, and
`점포명` are now allowed as safe merchant candidates in synthetic fixture-driven
tests. This does not permit arbitrary first-line merchant guessing.

---

## ADR-039: PaddleOCR quality improvement uses synthetic safe fixtures

Status: Accepted

Decision:
When live Azure comparison is blocked by quota or rate limits, PaddleOCR parser
quality work may proceed with synthetic sanitized PaddleOCR line fixtures and
expected `ReceiptRecord` field baselines.

Reason:
Synthetic safe fixtures let us test date, business number, payment method,
labeled amount, explicit VAT/supply, redaction, low-confidence, and numeric-noise
handling without customer receipts, provider raw output, live Azure calls, or
real PaddleOCR execution in default pytest.

Impact:
The quality path remains `paddle_lines -> StandardOCRResult ->
StandardOCRParserContext -> ReceiptParser.parse_standard_context() ->
ReceiptRecord`. Fixture tests can drive conservative parser improvements while
preserving the 10-A/B/C comparison contracts.

Risk:
Synthetic fixtures do not validate real image quality, skew, blur, glare,
wrinkles, detection misses, or model-runtime failures.

Response:
Use these fixtures as regression baselines now, then add optional non-sensitive
real OCR comparison once Azure quota and sample collection are stable.

2026-06-08 update:
A card-sales slip sample pattern was added as a saved Azure-anchor regression.
The fixture checks Paddle parser output for the Azure-visible core fields without
calling Azure again, and also validates explicit supply/VAT values when Paddle
lines expose them safely.

---

## ADR-040: New Job may select PaddleOCR for the current run

Status: Accepted

Decision:
The New Job screen may expose `PaddleOCR Local` as an explicit per-run OCR
provider option. This does not change the configured default provider.

Reason:
PaddleOCR quality work needs to be usable in the normal upload/review flow
without making local OCR a required dependency or replacing Azure/mock defaults.

Impact:
When selected, PaddleOCR output follows `StandardOCRResult ->
StandardOCRParserContext -> ReceiptParser.parse_standard_context() ->
ReceiptRecord`. The existing mock/Azure `OCRResult` parsing path remains
compatible, PaddleOCR PDF handling remains unsupported/deferred, and Excel export
plus Processing History contracts remain unchanged.

Guardrails:
The runtime path must not expose provider raw output, full OCR text, raw JSON,
full local paths, secrets, endpoint URLs, operation URLs, raw tracebacks, or
actual customer files. Default pytest must not require `paddleocr`, download OCR
models, or run real PaddleOCR OCR.

---

## ADR-041: Speed improvements must preserve OCR quality behavior

Status: Accepted

Decision:
PaddleOCR speed work may reuse expensive objects and cache pure repeated
calculations, but it must not skip OCR, parser, candidate, validation, fallback,
or review-required logic that can affect extraction quality.

Reason:
The New Job flow needs faster local OCR batches, but speed gains are not useful
if they hide missing fields or lower receipt extraction quality.

Impact:
`PaddleOCRProvider` can reuse the OCR engine instance within a provider object,
standard parser context construction can avoid duplicate candidate-map
extraction, and pure line compaction can use a bounded cache. These changes
preserve the same OCR result, parser input, and `ReceiptRecord` behavior.

Guardrails:
Rollback or correction is required if speed work changes parsed fields,
candidate hints, review status/reasons, validation warnings, default provider
selection, ExcelExporter output, Processing History schema, or raw-data exposure
rules.

---

## ADR-042: Review source preview stays inside upload boundaries

Status: Accepted

Decision:
The review screen may show an original receipt preview for the selected row, but
the file must be resolved from `stored_relative_path` under the configured upload
root. Full local paths are not shown.

Reason:
Reviewers need to compare OCR/parser results with the original image quickly, but
the UI must not become a generic local file browser or expose private path data.

Impact:
JPG/JPEG/PNG files can be shown with `st.image`; PDF files show a safe notice.
The selected receipt id and row number are stored in session state so reviewers
can move through rows consistently.

Guardrails:
Preview must block absolute paths, traversal paths, and files outside
`data/uploads`. It must not display OCR raw text, provider raw JSON, provider raw
output, full local paths, endpoint URLs, secrets, raw tracebacks, customer test
files, or sensitive raw values.

---

## ADR-043: Merchant dictionary data is a review candidate source

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-06-17 |
| 결정 | 상호/사업자번호 DB는 확정 DB가 아니라 검수 후보 생성을 위한 로컬 사전으로 둔다 |
| 이유 | 공공 상가정보에는 사업자번호가 없을 수 있고, OCR 결과는 항상 사용자 검수가 필요하기 때문 |
| 영향 | `merchant_master`, `merchant_alias`, `merchant_source_log` 테이블을 추가하고 기존 `ReceiptRecord`/ExcelExporter/처리 이력 흐름은 유지한다 |
| 리스크 | 후보 점수가 높아도 실제 거래처와 다를 수 있음 |
| 대응 | 후보는 `review_required=True`로만 반환하고, 사용자가 선택/수정할 때만 최종 상호가 바뀐다 |

Guardrails:

- Public CSV import stores allowed summary fields only.
- NTS API is limited to OCR-detected business-number status lookup and uses an
  `.env` key.
- Representative names, phone raw values, full OCR text, provider raw JSON, full
  local paths, raw API responses, mass collection, private crawling, automatic
  confirmation, and tax judgment are out of scope.

---

## ADR-044: Public merchant CSV refresh uses road-address hints

Status: Accepted

Decision:
The merchant dictionary may be refreshed about once per month from public store
CSV files. Import keeps only allowed public columns: merchant name, branch,
category, road name, building numbers, building name, and road address.

Reason:
Merchant-name fuzzy matching alone is weak for common store names. Road name and
building-number hints can narrow candidates while keeping the feature as a manual
review aid.

Impact:
`merchant_master` stores road-address hint columns, and `merchant_source_log`
stores an allowed-column file hash for duplicate-file detection. Settings can
import multiple CSV files sequentially without retaining the original files.
The Settings browser-upload path allows up to 400MB per CSV file; near-limit
imports should use the CLI path because it reads the local file directly.
Safe OCR parser lines may also provide transient road-address hints for review
candidate scoring, but these hints are not `ReceiptRecord` or Excel fields.

Guardrails:
Representative names, phone raw values, raw CSV rows, full local paths, Excel
candidate columns, automatic confirmation, and tax judgment remain out of scope.
Public CSV originals under `data/gov` or `govdata` must not be committed.

---

## ADR-045: Reviewed merchant names can become review aliases

Status: Accepted

Decision:
When users create the reviewed Excel output, safe reviewed merchant names may be
stored in `merchant_alias` with `source=review`. If the original parsed merchant
name differs from the reviewed merchant name, the original parsed value may also
be stored as an alias for future candidate matching.

Reason:
Public store data and OCR fuzzy matching are imperfect. User review corrections
are a useful local signal, especially for repeated OCR mistakes, but they must
remain candidate hints rather than automatic confirmations.

Impact:
Future merchant candidate lookup can rank review aliases before master fuzzy
matches. Alias rows may link to `merchant_master` when business number exact,
normalized name exact, or a high-confidence name match exists. Uncertain aliases
remain unlinked with nullable `merchant_master_id`.

Guardrails:
Alias learning skips empty, too-short, mostly numeric/symbolic,
business-number-like, phone-like, representative/owner-labeled, amount, date,
card, and approval-like values. It does not store raw OCR text, provider raw
JSON, full local paths, representative names, phone raw values, full addresses,
API keys, or raw tracebacks. Learned aliases do not overwrite `ReceiptRecord`,
ExcelExporter output, or Processing History receipt rows.

---

## ADR-046: Large public merchant CSV imports prefer CLI with safe performance summaries

Status: Accepted

Decision:
For near-400MB public merchant CSV files, the CLI import path is the preferred
operational path. The Settings UI can still import files up to the configured
upload limit, but browser upload overhead makes it less suitable for large
monthly refreshes.

Reason:
The CLI reads the local CSV directly and can use chunked SQLite bulk inserts in
one import transaction. This avoids Streamlit browser upload overhead and gives
operators a clear performance summary.

Impact:
Importer results include safe summary fields: file name, batch id, scanned row
count, imported/skipped counts, duplicate-file status, elapsed seconds, and rows
per second. Duplicate files are skipped by allowed-column file hash; duplicate
rows are skipped by allowed-column row hash and SQLite uniqueness.

Guardrails:
Summaries must not include full local paths, raw CSV rows, representative names,
phone raw values, blocked columns, raw OCR text, provider raw JSON, API keys, or
raw tracebacks. Failed imports must not leave partial merchant rows or duplicate
source logs. ExcelExporter, ReceiptRecord, and Processing History schemas remain
unchanged.

---

## ADR-047: Merchant candidate quality diagnostics are manual safe summaries

Status: Accepted

Decision:
Merchant dictionary and matcher quality diagnostics are provided as explicit
operator actions in Settings. They show safe dictionary aggregates, masked
candidate results for synthetic inputs, and optional saved ReceiptRecord
aggregate diagnostics.

Reason:
Operators need a way to check whether public merchant data, address hints, and
review aliases are improving candidate quality without exposing customer OCR raw
text or accidentally confirming candidates.

Impact:
The diagnostic flow can read merchant dictionary tables and safe receipt fields.
It can show counts, score buckets, match-type counts, and limited safe samples.
Business numbers are masked, and candidates remain review-required hints.

Guardrails:
Diagnostics do not run bulk saved-record checks automatically. They must not
store or display raw OCR text, provider raw JSON, full local paths, phone raw
values, representative names, raw CSV rows, API keys, or raw tracebacks. They do
not change `ReceiptRecord`, ExcelExporter output, Processing History schema,
matcher thresholds, NTS behavior, OpenAI behavior, or review status.
## ADR-048: Merchant dictionary search is bounded and candidate scoring favors review quality

Status: Accepted

Decision:
Settings may provide a bounded merchant dictionary search by merchant-name query
or road-name plus building-number query. Very short public-store substring
matches stay below the fuzzy threshold unless a safe address hint boosts them.

Reason:
The public merchant database can be large and can contain many tenants at the
same building. Broad address or short-name matches can create noisy candidates
that look worse than the parser result. Search and matcher output should help
manual review without pretending to confirm the merchant.

Impact:
Operators can inspect merchant dictionary rows without opening the CSV, review
source preview does less full-table work, and short fuzzy candidates such as
tiny prefixes are less likely to crowd the review table unless address evidence
supports them.

Guardrails:
Candidates remain `review_required=True`. No raw OCR text, provider raw JSON,
full local paths, raw CSV rows, phone raw values, representative names, API keys,
or full business numbers are displayed or stored by this diagnostic/search flow.
ReceiptRecord, ExcelExporter, and Processing History schemas remain unchanged.

---

## ADR-049: Real sample quality checks are manual safe summaries

Status: Accepted

Decision:
Real PaddleOCR sample checks are run only as manual/opt-in quality reviews.
Default pytest must not call real PaddleOCR, download OCR models, or require live
OCR provider access.

Reason:
The project needs real-image quality checks, but they can be slow,
environment-dependent, and privacy-sensitive. Keeping them manual preserves fast
deterministic tests while still allowing targeted quality validation.

Impact:
Operators may verify individual samples by visually checking the receipt and
comparing safe parsed fields. Reports should distinguish current-code
reprocessing results from stale Processing History rows.

Guardrails:
Manual sample reports may include file name, expected visible merchant/date/
amount/payment method, parsed fields, address-hint presence, top candidate
summary, and mismatch status. They must not include raw OCR text, provider raw
JSON, full local paths, raw CSV rows, representative names, phone raw values,
API keys, raw tracebacks, or full business numbers. They must not auto-confirm
candidates or change ReceiptRecord, ExcelExporter, or Processing History schemas.

---
