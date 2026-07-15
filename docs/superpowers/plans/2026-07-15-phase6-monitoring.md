# Phase 6 — 모니터링 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or plain inline execution) to implement this plan task-by-task. No reviewer subagent is dispatched for this project — see project feedback memory. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 상태별 주문 수(REJECTED 제외)와 시료별 재고 현황(여유/부족/고갈)을
조회하는 `MonitoringController`를 추가한다. PRD 예시 UI(19페이지)와 동일하게
"주문량 확인"/"재고량 확인" 두 서브메뉴로 분리한다.

**Architecture:** `MonitoringController(order_repository, sample_repository, view)`.
Phase 1의 `OrderRepository.list_by_status()`를 상태 4종(`RESERVED, CONFIRMED,
PRODUCING, RELEASED`)에 대해 호출해 주문 수를 센다. 재고 현황은 시료별
"미해결 수요"(아직 재고에 정산되지 않은 주문 수량 합)를 계산해 재고량과
비교한다 — Phase 4/5 수정 이후 `RESERVED`/`PRODUCING` 상태 주문만 재고에
아직 반영되지 않았고, `CONFIRMED`/`RELEASED`는 이미 정산 완료 상태이기
때문이다 (승인 시 즉시 차감하거나, 생산 완료 시 `actual_qty - qty`로 차감).

**Tech Stack:** Python 3.13, pytest. 신규 SQL 스키마 변경 없음.

## Global Constraints

- 주문량 확인은 `RESERVED/CONFIRMED/PRODUCING/RELEASED` 4개 상태의 건수만
  센다. `REJECTED`는 유효한 주문이 아니므로 집계에서 제외한다(PRD 9장).
- 재고 상태 판정(우선순위 순):
  1. `stock_qty == 0` → **고갈**
  2. `stock_qty >= demand` → **여유**
  3. 그 외(`0 < stock_qty < demand`) → **부족**
  여기서 `demand`는 해당 시료에 대한 `RESERVED`+`PRODUCING` 상태 주문의
  수량 합(다른 상태는 이미 재고에 정산됨).
- 컨트롤러 테스트는 실제 SQLite(`tmp_path`)를 쓰고 view만 기록용 페이크로
  대체한다 (mock 금지). `run()`의 메뉴 루프는 테스트하지 않는다.
- 이 프로젝트는 리뷰어 서브에이전트를 쓰지 않는다: 계획 확정 → 구현 → 테스트
  통과 확인 → 커밋 순으로 진행한다.

---

### Task 1: `MonitoringController` + 콘솔 뷰 확장

**Files:**
- Modify: `view/console_view.py` (함수 추가, 기존 함수는 그대로 유지)
- Create: `controller/monitoring_controller.py`
- Test: `test_monitoring_controller.py`

**Interfaces:**
- Consumes: `model.order.OrderStatus`, `model.order_repository.SqliteOrderRepository`,
  `model.sample_repository.SqliteSampleRepository`,
  `model.sample_id_format.format_sample_id`
- Produces: `MonitoringController(order_repository, sample_repository, view) -> None`,
  공개 메서드 `run()`. `view` 프로토콜에 다음 함수가 필요:
  `prompt_monitor_menu() -> str`,
  `show_order_counts(counts: list[tuple[OrderStatus, int]]) -> None`,
  `show_inventory_status(entries: list[tuple[Sample, int, str]]) -> None`.

- [ ] **Step 1: `view/console_view.py`에 모니터링 메뉴 함수 추가**

파일 끝에 이어서 추가:

```python
MONITOR_MENU_TEXT = """
1. 주문량 확인
2. 재고량 확인
0. 뒤로
"""


def prompt_monitor_menu() -> str:
    print(MONITOR_MENU_TEXT)
    return input("선택 > ")


def show_order_counts(counts: list) -> None:
    for status, count in counts:
        print(f"{status.value}: {count}건")


def show_inventory_status(entries: list) -> None:
    for sample, demand, state in entries:
        print(
            f"[{format_sample_id(sample.id)}] {sample.name} | 재고 {sample.stock_qty}ea "
            f"| 주문대비 수요 {demand}ea | 상태 {state}"
        )
```

- [ ] **Step 2: 실패하는 테스트 작성 — `test_monitoring_controller.py`**

```python
from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.order import Order, OrderStatus
from model.order_repository import SqliteOrderRepository
from controller.monitoring_controller import MonitoringController


class _FakeView:
    def __init__(self):
        self.order_counts = None
        self.inventory_entries = None

    def show_order_counts(self, counts):
        self.order_counts = counts

    def show_inventory_status(self, entries):
        self.inventory_entries = entries


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path)


def _order(order_repo, sample_id, qty, status):
    order = order_repo.add(
        Order(id=None, order_no=None, sample_id=sample_id, customer_name="A",
              qty=qty, status=OrderStatus.RESERVED, created_at=None)
    )
    if status != OrderStatus.RESERVED:
        order = order_repo.update_status(order.id, status)
    return order


def test_show_order_counts_excludes_rejected(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=100))
    _order(order_repo, sample.id, 10, OrderStatus.RESERVED)
    _order(order_repo, sample.id, 10, OrderStatus.CONFIRMED)
    _order(order_repo, sample.id, 10, OrderStatus.CONFIRMED)
    _order(order_repo, sample.id, 10, OrderStatus.PRODUCING)
    _order(order_repo, sample.id, 10, OrderStatus.RELEASED)
    _order(order_repo, sample.id, 10, OrderStatus.REJECTED)
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_order_counts()

    counts = dict(view.order_counts)
    assert counts[OrderStatus.RESERVED] == 1
    assert counts[OrderStatus.CONFIRMED] == 2
    assert counts[OrderStatus.PRODUCING] == 1
    assert counts[OrderStatus.RELEASED] == 1
    assert OrderStatus.REJECTED not in counts


def test_show_inventory_status_reports_surplus_when_stock_covers_demand(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=100))
    _order(order_repo, sample.id, 30, OrderStatus.RESERVED)
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_inventory_status()

    entry = next(e for e in view.inventory_entries if e[0].id == sample.id)
    assert entry[1] == 30
    assert entry[2] == "여유"


def test_show_inventory_status_reports_shortage_when_demand_exceeds_stock(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=10))
    _order(order_repo, sample.id, 5, OrderStatus.RESERVED)
    _order(order_repo, sample.id, 10, OrderStatus.PRODUCING)
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_inventory_status()

    entry = next(e for e in view.inventory_entries if e[0].id == sample.id)
    assert entry[1] == 15
    assert entry[2] == "부족"


def test_show_inventory_status_reports_depleted_when_stock_zero_even_without_demand(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_inventory_status()

    entry = next(e for e in view.inventory_entries if e[0].id == sample.id)
    assert entry[1] == 0
    assert entry[2] == "고갈"


def test_show_inventory_status_ignores_confirmed_and_released_demand(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=5))
    _order(order_repo, sample.id, 1000, OrderStatus.CONFIRMED)
    _order(order_repo, sample.id, 1000, OrderStatus.RELEASED)
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_inventory_status()

    entry = next(e for e in view.inventory_entries if e[0].id == sample.id)
    assert entry[1] == 0
    assert entry[2] == "여유"
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_monitoring_controller.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.monitoring_controller'` 로 전부 실패.

- [ ] **Step 4: `controller/monitoring_controller.py` 구현**

```python
from model.order import OrderStatus

EXIT_CHOICE = "0"
ORDER_COUNT_STATUSES = [OrderStatus.RESERVED, OrderStatus.CONFIRMED, OrderStatus.PRODUCING, OrderStatus.RELEASED]
DEMAND_STATUSES = [OrderStatus.RESERVED, OrderStatus.PRODUCING]


class MonitoringController:
    def __init__(self, order_repository, sample_repository, view) -> None:
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_monitor_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._show_order_counts()
            elif choice == "2":
                self._show_inventory_status()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _show_order_counts(self) -> None:
        counts = [
            (status, len(self._order_repository.list_by_status(status)))
            for status in ORDER_COUNT_STATUSES
        ]
        self._view.show_order_counts(counts)

    def _show_inventory_status(self) -> None:
        demand_by_sample = self._demand_by_sample()
        entries = []
        for sample in self._sample_repository.list_all():
            demand = demand_by_sample.get(sample.id, 0)
            entries.append((sample, demand, self._inventory_state(sample.stock_qty, demand)))
        self._view.show_inventory_status(entries)

    def _demand_by_sample(self) -> dict[int, int]:
        demand: dict[int, int] = {}
        for status in DEMAND_STATUSES:
            for order in self._order_repository.list_by_status(status):
                demand[order.sample_id] = demand.get(order.sample_id, 0) + order.qty
        return demand

    @staticmethod
    def _inventory_state(stock_qty: int, demand: int) -> str:
        if stock_qty == 0:
            return "고갈"
        if stock_qty >= demand:
            return "여유"
        return "부족"
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_monitoring_controller.py -v`
Expected: 5개 테스트 모두 `PASSED`.

- [ ] **Step 6: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add view/console_view.py controller/monitoring_controller.py test_monitoring_controller.py
git commit -m "feat: add MonitoringController for order counts and inventory status"
```

---

### Task 2: 단독 실행 진입점 `monitoring_menu.py`

**Files:**
- Create: `monitoring_menu.py`

**Interfaces:**
- Consumes: `controller.monitoring_controller.MonitoringController`,
  `model.order_repository.SqliteOrderRepository`,
  `model.sample_repository.SqliteSampleRepository`, `view.console_view`
- Produces: 없음 (Phase 8에서 통합 `main.py`가 이 컨트롤러를 메뉴 중 하나로 흡수)

- [ ] **Step 1: `monitoring_menu.py` 작성**

```python
from controller.monitoring_controller import MonitoringController
from model.order_repository import SqliteOrderRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    MonitoringController(SqliteOrderRepository(), SqliteSampleRepository(), console_view).run()
```

- [ ] **Step 2: 수동 스모크 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -c "import ast; ast.parse(open('monitoring_menu.py', encoding='utf-8').read())"`
Expected: 에러 없이 종료.

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add monitoring_menu.py
git commit -m "feat: add standalone monitoring_menu.py entrypoint"
```

---

### Task 3: 전체 검증 및 푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 55개(Phase 1~5) + 신규 `test_monitoring_controller.py` 5개 =
총 60개 모두 `PASSED`.

- [ ] **Step 2: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
