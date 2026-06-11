# Local OCR Runtime Strategy

## 목적

Azure OCR은 현재 품질 기준선으로 유지하되, 장기적으로 전체 처리량이 Azure 비용에 고정되지 않도록 PC Local OCR Runtime과 Server Runtime 후보를 검토합니다.

## 웹은 입력/검수 UI

웹은 OCR 엔진이 아니라 다음 역할에 집중합니다.

- 파일 업로드
- 진행 상태 표시
- 사용자 검수
- 표준 엑셀 다운로드
- 처리 이력 조회와 기존 export 재다운로드
- 읽기 전용 설정/상태 확인

실제 OCR 처리는 PC Local Runtime 또는 Server Runtime에서 수행할 수 있습니다.

## PC Local OCR Runtime 구조

PC Local OCR Runtime은 사용자의 PC 또는 사무실 PC에 OCR 엔진을 설치하고, 웹/Streamlit UI가 해당 Runtime을 호출하는 구조입니다.

기본 흐름:

```text
웹/Streamlit 업로드
→ Local OCR Runtime 호출
→ Provider Adapter가 StandardOCRResult 생성
→ ReceiptParser
→ ReceiptValidator / CategoryRules / CardMatcher
→ ExcelExporter
→ Processing History
```

## PaddleOCR Local Provider 후보

PaddleOCR은 PC Local OCR Runtime의 1차 후보입니다.

검토 항목:

- 한국어 영수증 인식 품질
- Windows 설치 난이도
- 모델 용량
- CPU/GPU 처리 속도
- PDF 처리 방식
- PaddleOCR 미설치 환경에서의 안전한 실패 안내

## Tesseract 후보

Tesseract는 경량 대안 후보입니다.

검토 항목:

- 설치 난이도
- 한국어 인식 품질
- 영수증 레이아웃 대응력
- PaddleOCR 대비 처리 속도와 정확도

## Azure fallback 위치

Azure는 제거하지 않습니다. 다만 장기적으로 전체 기본 처리 엔진이 아니라 다음 위치에 둡니다.

- 검토필요 건 고정확도 재처리
- 유료 재처리 옵션
- 사무실 플랜의 fallback
- PaddleOCR/Tesseract 실패 건 재처리
- 품질 비교 기준선

초기 fallback 후보 기준은 `docs/ocr_quality_comparison_contract.md`의 10주차-A 계약을 따릅니다. PaddleOCR 실패, 핵심 필드 누락, 금액 후보 분리 실패, 반복적인 검토 필요 신호, low confidence 라인 비율, 환경 실패율 또는 처리시간 문제가 후보 신호입니다. 이 기준은 자동 세무 판단이 아니라 사용자 검수 또는 유료 재처리 후보 표시 기준입니다.

## Streamlit Local Edition

초기 PoC는 기존 Streamlit 구조를 유지하고 `OCR_PROVIDER=paddle` 후보를 추가하는 방향으로 검토합니다.

원칙:

- PaddleOCR 미설치 환경에서도 기본 pytest가 실패하지 않아야 합니다.
- PaddleOCR Provider는 `StandardOCRResult`를 반환해야 합니다.
- Parser는 PaddleOCR 원본 응답을 직접 알면 안 됩니다.

## Docker Compose Edition

사무실/PC 설치 부담을 낮추기 위해 Docker Compose Edition을 후속 후보로 검토합니다.

장점:

- OCR Runtime 의존성 격리
- 설치 절차 표준화
- 업데이트 관리 용이

리스크:

- Docker Desktop 설치 필요
- 비개발 사용자에게 초기 진입 장벽 가능
- GPU/성능 설정 복잡성

## Tauri/Electron Desktop 후보

파일럿 이후 반복 사용이 확인되면 Desktop App 포장을 검토합니다.

후보:

- Tauri Desktop
- Electron Desktop
- Python 패키징 기반 로컬 앱

목표:

- 로컬 파일 접근과 OCR Runtime 실행을 안정화합니다.
- 사용자는 웹처럼 쓰되 설치형 앱처럼 실행할 수 있게 합니다.

## 사무실/PC 사용자 시나리오

1. 사무실 PC에서 로컬 앱 또는 Streamlit Local Edition 실행
2. 영수증 이미지/PDF와 카드 사용내역 업로드
3. PaddleOCR 또는 Tesseract로 1차 OCR
4. 검토필요 건만 Azure fallback 후보로 표시
5. 사용자 검수 후 표준 엑셀 생성
6. 처리 이력에서 기존 export 재다운로드

## 설치/업데이트/성능/보안 리스크

| 리스크 | 설명 | 대응 |
|---|---|---|
| 설치 | PaddleOCR, Tesseract, 모델 파일 설치가 어렵다 | Streamlit Local Edition PoC 후 Docker/Desktop 포장 검토 |
| 업데이트 | OCR 모델과 앱 버전 불일치 가능 | Runtime 버전과 schema_version 기록 |
| 성능 | CPU 환경에서 처리 속도가 느릴 수 있다 | 샘플 기준 평균 처리시간 측정 |
| 보안 | 로컬 파일 경로와 OCR 원문 노출 위험 | 전체 경로와 raw text/raw JSON 전체 미노출 원칙 유지 |
| 품질 | 무료 OCR 정확도가 Azure보다 낮을 수 있다 | Azure fallback 기준과 Golden Fixture 비교 |

## Azure 비용 절감 효과

Local OCR Runtime은 모든 영수증을 Azure로 보내는 구조를 피합니다. 기본 처리는 로컬 OCR로 수행하고, 검토필요 건이나 유료 재처리 건만 Azure fallback으로 보낼 수 있습니다.

## 후속 PoC 계획

1. `StandardOCRResult` fixture와 expected `ReceiptRecord` fixture 준비
2. Azure Adapter를 `StandardOCRResult` 기준으로 정리
3. Parser 입력을 `StandardOCRResult` 중심으로 정리
4. `OCR_PROVIDER=paddle` PoC 후보 작성
5. Azure vs PaddleOCR 품질/속도 비교
6. Docker Compose 또는 Desktop App 포장 후보 검토
## Week 10-B Safe Preview Link

PaddleOCR smoke-test results may be shown through the safe preview utility after conversion to `StandardOCRResult`. The preview is limited to safe `text_blocks` rows, confidence labels, low-confidence flags, and redaction/category counts.

This preview is a manual review aid only. It is not an automatic tax judgment, not a provider default switch, and not Azure fallback automation. Full OCR raw text, PaddleOCR raw output, full local paths, and customer files remain excluded from UI, logs, DB, Excel, fixtures, and test output.
## Week 10-C Side-by-side Comparison Link

The local PaddleOCR runtime can now be exercised in an explicit Azure vs PaddleOCR side-by-side settings diagnostic. This diagnostic uses one non-sensitive image sample and compares the PaddleOCR result against Azure only after both are represented as `StandardOCRResult` and parsed through the standard parser context.

Fallback remains a review/reprocessing candidate concept, not an automatic tax decision or automatic provider retry. Week 10-C records safe per-sample signals such as status, diagnostic code, sanitized diagnostic detail code, elapsed time, low-confidence count, redacted count, and field match status. Week 10-D is responsible for aggregating those signals and documenting fallback thresholds.

Local sample testing showed PaddleOCR completing 10/10 image runs in the current environment, while Azure can return `analyze_http_403` with safe detail `quota_or_rate_limit` when the Azure resource is currently quota-limited or rate-limited. That condition should be counted as an Azure environment/service availability signal in Week 10-D, not as a PaddleOCR quality failure.

PaddleOCR line-derived candidate hints should remain conservative. Clearly labeled merchant names, date, business number, payment method, and clearly labeled amount candidates are acceptable. Arbitrary first-line merchant guesses and unlabeled maximum-amount guesses remain deferred because they produced misleading field matches in early sample testing.

## Week 10-D-prep Synthetic Fixture Path

When Azure is unavailable, quota-limited, or rate-limited, local OCR quality work
can continue with synthetic sanitized PaddleOCR fixtures. These fixtures are safe
line-level inputs that are converted to `StandardOCRResult` and parsed through
`StandardOCRParserContext`; they are not provider raw output, not full OCR text
dumps, and not customer receipts.

This path is useful for improving conservative parser behavior around labeled
merchant names, dates, business numbers, payment methods, labeled amounts,
explicit supply/VAT fields, redacted sensitive lines, OCR amount character
corrections, and numeric noise guards. It does not validate real image quality or
model-runtime behavior, so optional real-sample OCR comparison remains a later
step after Azure quota/sample availability recovers.
