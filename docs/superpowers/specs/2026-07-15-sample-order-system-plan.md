# 반도체 시료 생산주문관리 시스템 - 개발 계획

## 배경

현재 저장소에는 이전 "ConsoleMVC" PoC 과제에서 사용한 범용 `Item` CRUD 스켈레톤
(`model/repository.py`의 InMemory/Csv/Json/Sqlite Repository, `ItemController`,
`SeedController`, `MonitorController`)이 그대로 들어와 있다. 이번 과제는 이 골격을
"반도체 시료 생산주문관리 시스템" 기능 명세(`[CRA_AI] Day3_개인과제_반도체시료관리_r1 2.pdf`)에
맞춰 Sample/Order/생산라인 도메인으로 교체 개발하는 것이다.

## 확정한 설계 방향

- **영속성**: SQLite로 고정. 기존 Repository 패턴(ABC + 구현체)은 유지하되 `Sample`,
  `Order` 두 엔티티에 맞춰 재작성한다.
- **생산 라인 시간 흐름**: 백그라운드 스레드로 실시간 진행. 생산 시작 시각을 기록하고,
  실제 생산시간(분)만큼 경과하면 `PRODUCING → CONFIRMED`로 자동 전환한다. 콘솔에서는
  진행률(%)을 조회할 수 있다.
- **생산 라인 수**: 명세대로 단일 라인, FIFO 큐.

## 도메인 모델

- **Sample (시료)**: `id, name(고유), avg_production_time, yield_rate, stock_qty`
- **Order (주문)**: `id, sample_id, customer_name, qty, status, created_at`
  - 상태: `RESERVED → REJECTED` 또는 `RESERVED → CONFIRMED` 또는
    `RESERVED → PRODUCING → CONFIRMED → RELEASE`
- **ProductionJob**: `order_id, shortage_qty, actual_qty = ceil(shortage_qty / yield_rate),
  total_time = avg_production_time * actual_qty, started_at`

## Phase별 개발 계획

**Phase 0 — 준비**
- 기존 `Item`/`ItemController`/`CsvRepository` 등 범용 스켈레톤 제거
- `PRD.md`(기능 명세 정리), `CLAUDE.md`(도메인 규칙·상태 전이 규칙) 작성

**Phase 1 — 모델 & 영속성 계층**
- `model/sample.py`, `model/order.py` dataclass
- `model/sample_repository.py`, `model/order_repository.py` (SQLite, CRUD + 상태별 조회)
- 단위 테스트: repository CRUD

**Phase 2 — 시료 관리 기능**
- 시료 등록 / 조회(재고 포함) / 이름 검색 controller + view
- 테스트: 등록 검증, 검색

**Phase 3 — 주문 접수(예약)**
- 시료ID/고객명/수량 입력 → RESERVED 주문 생성, 주문번호 채번(`ORD-YYYYMMDD-NNNN`)
- 테스트: 존재하지 않는 시료ID 처리, 정상 접수

**Phase 4 — 주문 승인/거절**
- RESERVED 목록 조회
- 승인 시 재고 비교: 충분 → CONFIRMED / 부족 → 생산 큐 등록 + PRODUCING
- 거절 시 즉시 REJECTED
- 테스트: 재고 충분/부족 분기, 거절 흐름

**Phase 5 — 생산 라인(백그라운드 스레드)**
- FIFO 생산 큐 + 스레드로 순차 처리 (실생산량/총시간 계산식 적용)
- 완료 시 재고 가산, 주문 PRODUCING → CONFIRMED 전환
- 생산 현황/대기 큐 조회 뷰
- 테스트: FIFO 순서, 실생산량/시간 계산, 스레드 안전성(락)

**Phase 6 — 모니터링**
- 상태별(REJECTED 제외) 주문 수 집계
- 시료별 재고 상태(여유/부족/고갈) 판정
- 테스트: 판정 임계값 로직

**Phase 7 — 출고 처리**
- CONFIRMED 목록 조회 → 선택 출고 → RELEASE 전환
- 테스트: 상태 가드(CONFIRMED 아닌 주문 출고 시도 시 에러)

**Phase 8 — 통합 & 더미데이터/모니터 도구**
- 메인 메뉴(main.py) 통합, 시스템 현황 요약 표시
- `seed_controller`를 Sample/Order 도메인으로 개조
- `monitor.py`를 신규 스키마 기준으로 개조
- 엔드투엔드 시나리오 테스트 (접수 → 승인 → 생산 → 출고)

**Phase 9 — 마무리**
- 클린코드 리뷰(중복 제거, 네이밍), 테스트 커버리지 점검
- 커밋 이력 정리, README/PRD 최종화
