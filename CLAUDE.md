# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code(및 협업자)를 위한 규칙을
정리한다. 기능 명세의 전체 내용은 `PRD.md`를 참조한다.

## 프로젝트 구조

- `model/` — 도메인 엔티티(dataclass)와 Repository(영속성 계층)
- `controller/` — 메뉴별 유스케이스 로직 (View와 Model을 연결)
- `view/` — 콘솔 입출력 전용, 비즈니스 로직 금지
- `docs/superpowers/specs/` — 설계 문서, `docs/superpowers/plans/` — 구현 계획
- 테스트 파일은 대상 모듈과 같은 계층에 `test_*.py` 로 둔다 (기존 관례:
  `test_seed_controller.py` 처럼 controller 이름 + `test_` 접두어).

## 도메인 규칙

### 엔티티

- **Sample**: `id, name(고유), avg_production_time(min/ea), yield_rate(0~1), stock_qty`
- **Order**: `id, sample_id, customer_name, qty, status, created_at`

### 주문 상태 (5종, `RELEASED`로 표기 통일)

| 상태 | 의미 |
|---|---|
| RESERVED | 주문 접수 |
| REJECTED | 주문 거절 (모니터링/집계 대상 제외) |
| PRODUCING | 승인 완료, 재고 부족으로 생산 중 |
| CONFIRMED | 승인 완료, 출고 대기 중 |
| RELEASED | 출고 완료 |

> PDF 원문은 흐름도에서 `RELEASED`, 표에서는 `RELEASE`로 표기가 엇갈린다.
> 다른 상태(`RESERVED/REJECTED/CONFIRMED`)와 동일한 과거분사형 패턴을
> 따르기 위해 이 프로젝트에서는 `RELEASED`로 통일한다.

허용된 전이만 구현한다:
```
RESERVED -> REJECTED
RESERVED -> CONFIRMED           (재고 충분)
RESERVED -> PRODUCING -> CONFIRMED   (재고 부족 -> 생산 완료)
CONFIRMED -> RELEASED
```
그 외 전이(예: REJECTED에서 재승인, RELEASED에서 재출고)는 에러로 처리한다.

### 생산 계산식

- 실 생산량 = `math.ceil(부족분 / 수율)`
- 총 생산 시간(분) = `평균 생산시간 * 실 생산량`
- 생산 큐는 FIFO. 생산 완료 시 재고에 실 생산량을 더하고 주문을
  `PRODUCING -> CONFIRMED` 로 전환한다.

## 기술 스택 / 컨벤션

- Python 3.13, 표준 라이브러리 `sqlite3`, `threading`, `queue`만 사용
  (외부 의존성 추가 전 표준 라이브러리로 해결 가능한지 먼저 검토).
- 엔티티는 `@dataclass`, 타입힌트 필수.
- Repository는 추상 베이스(ABC) + 구현체 패턴을 유지한다(`SampleRepository`/
  `OrderRepository`/`ProductionQueueRepository` 모두 SQLite 구현체 하나만 유지).
- 생산 라인 백그라운드 스레드는 `threading.Lock`으로 재고/큐 접근을 보호한다.

## 테스트 정책

- `pytest` 사용, TDD로 진행 (실패하는 테스트 먼저 작성 → 구현 → 통과 확인).
- Repository/Controller 단위 테스트를 우선하고, 마지막 Phase에서 접수→승인→
  생산→출고 전체 흐름의 엔드투엔드 테스트를 추가한다.

## 커밋 정책

- Phase별 계획 문서(`docs/superpowers/plans/`)의 Task 단위로 커밋한다.
- 커밋 메시지는 `feat:`, `fix:`, `docs:`, `chore:`, `test:` 접두어를 사용한다.

## 실행 방법 (Phase 1 이후 유효)

- `python main.py` — 콘솔 메인 메뉴 실행
- `python seed.py` — 더미 시료/주문 데이터 생성
- `python monitor.py` — 실시간 데이터 조회 도구
- `pytest` — 전체 테스트 실행

## 테스트 커버리지 감사 (Phase 9)

모든 `model/*.py`, `controller/*.py` 모듈은 대응하는 `test_*.py`를 가진다:

| 모듈 | 테스트 |
|---|---|
| `model/sample_repository.py` | `test_sample_repository.py` |
| `model/sample_id_format.py` | `test_sample_id_format.py` |
| `model/order_repository.py` | `test_order_repository.py` |
| `model/production_queue_repository.py` | `test_production_queue_repository.py` |
| `controller/sample_controller.py` | `test_sample_controller.py` |
| `controller/order_controller.py` | `test_order_controller.py` |
| `controller/approval_controller.py` | `test_approval_controller.py` |
| `controller/production_line_worker.py` | `test_production_line_worker.py` |
| `controller/production_line_controller.py` | `test_production_line_controller.py` |
| `controller/monitoring_controller.py` | `test_monitoring_controller.py` |
| `controller/release_controller.py` | `test_release_controller.py` |
| `controller/main_menu_controller.py` | `test_main_menu_controller.py` |
| `controller/live_monitor_controller.py` | `test_live_monitor_controller.py` |
| `controller/seed_controller.py` | `test_seed_controller.py` |
| 전체 통합 흐름 | `test_end_to_end_order_flow.py` |

`model/sample.py`, `model/order.py`, `model/production_job.py`는 순수
dataclass/Enum이라 별도 테스트 없이 위 리포지토리 테스트들이 간접적으로
검증한다.

**의도적으로 테스트하지 않은 부분:** `view/console_view.py`는 `print`/`input`
호출만 있는 순수 I/O 계층이라 직접 단위 테스트가 없다 — 모든 컨트롤러
테스트가 view를 페이크로 교체해 호출 여부만 검증하고, 실제 콘솔 출력
포맷은 수동 확인 대상으로 남긴다. 이 계층에 조건 분기나 계산 로직이
추가되면 그때 테스트를 추가한다.
