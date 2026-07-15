# 반도체 시료 생산주문관리 시스템

콘솔 기반으로 반도체 시료(Sample)의 등록/주문/승인/생산/출고를 관리하는
시스템. 기능 명세는 [`PRD.md`](PRD.md), 개발 규칙은 [`CLAUDE.md`](CLAUDE.md)
참고.

## 실행 방법

```bash
python main.py
```

메인 메뉴에서 시료 관리 / 시료 주문 / 주문 승인·거절 / 모니터링 /
생산라인 조회 / 출고 처리를 선택해 사용한다. 데이터는 `data/sampleorder.db`
(SQLite)에 저장되어 재실행해도 유지된다.

생산 라인은 백그라운드 스레드로 동작하며, 시뮬레이션 1분당 실제 대기
시간은 `PRODUCTION_TIME_SCALE` 환경변수로 조절한다 (기본값 `1.0` = 60배
가속, `60`을 주면 실제 시간 그대로 흐름):

```bash
PRODUCTION_TIME_SCALE=60 python main.py
```

## 더미 데이터 생성

```bash
python seed.py
```

랜덤 시료 10종과 주문 20건(`RESERVED` 상태)을 DB에 추가한다.

## 실시간 데이터 조회 도구

```bash
python monitor.py
```

2초 간격으로 전체 시료/주문 현황을 콘솔에 출력한다 (`Ctrl+C`로 종료).

## 테스트

```bash
pytest
```

## 프로젝트 구조

- `model/` — 도메인 엔티티(`Sample`, `Order`, `ProductionJob`)와 SQLite Repository
- `controller/` — 메뉴별 유스케이스 로직 (`SampleController`, `OrderController`,
  `ApprovalController`, `ProductionLineWorker`/`ProductionLineController`,
  `MonitoringController`, `ReleaseController`, `MainMenuController`,
  `SeedController`, `LiveMonitorController`)
- `view/` — 콘솔 입출력 전용 (`console_view.py`)
- `docs/superpowers/` — 설계 문서(`specs/`)와 Phase별 구현 계획(`plans/`)
