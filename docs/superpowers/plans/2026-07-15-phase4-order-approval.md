# Phase 4 — 주문 승인/거절 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or plain inline execution) to implement this plan task-by-task. No reviewer subagent is dispatched for this project — see project feedback memory. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 생산 담당자가 `RESERVED` 주문 목록을 보고 특정 주문을 승인 또는
거절하는 `ApprovalController`를 추가한다. 승인 시 재고 상황에 따라 즉시
`CONFIRMED`로 전환하거나(재고 충분), 생산 큐에 등록하고 `PRODUCING`으로
전환한다(재고 부족). 생산 큐에 쌓인 작업을 실제로 처리하는 백그라운드
스레드는 Phase 5에서 만든다 — 이번 Phase는 큐에 등록하는 지점까지만 만든다.

**Architecture:** PRD 11장 예시 UI(페이지 17)처럼 "목록 표시 → 번호 선택 →
Y/N 승인 결정"을 한 번의 상호작용으로 처리한다(시료 관리처럼 승인/거절을
별도 서브메뉴로 나누지 않음). `ApprovalController`는 `order_repository`,
`sample_repository`, `production_queue_repository`, `view` 네 개를
주입받는다. 생산 큐는 새 모델/리포지토리 쌍
`model/production_job.py` + `model/production_queue_repository.py`로
Phase 1과 동일한 ABC + SQLite 구현체 패턴을 따르고, 이번 Phase에서는
`enqueue`/`list_pending`만 만든다(대기열 소진·처리는 Phase 5 책임).

**Tech Stack:** Python 3.13 표준 라이브러리 `sqlite3`, `math`, `datetime`,
pytest. Phase 1의 `Order`/`OrderStatus`/`SqliteOrderRepository`,
Phase 1의 `Sample`/`SqliteSampleRepository`, Phase 2의
`model.sample_id_format.format_sample_id`를 그대로 재사용한다.

## Global Constraints

- 실 생산량 = `math.ceil(부족분 / 수율)`, 총 생산 시간 = `평균 생산시간 * 실 생산량`
  (`CLAUDE.md`/`PRD.md` 10장 공식 그대로).
- 재고 비교는 `sample.stock_qty >= order.qty`를 "충분"으로 판단한다(같으면
  충분). 충분하면 `sample_repository.update_stock(sample_id, -order.qty)`로
  즉시 차감하고 주문을 `CONFIRMED`로 전환한다. 부족하면 재고는 그대로 두고
  (생산 완료 시점에 Phase 5가 가산) 부족분만큼 생산 큐에 등록하고 주문을
  `PRODUCING`으로 전환한다.
- 승인 대상 선택은 방금 표시한 `RESERVED` 목록의 1부터 시작하는 번호로 받는다.
  범위를 벗어나거나 숫자가 아니면 에러 처리하고 아무 것도 바꾸지 않는다.
- 승인/거절 결정은 `Y`/`N`(대소문자 무관)만 허용한다. 그 외 입력은 에러
  처리하고 아무 것도 바꾸지 않는다.
- 생산 큐 레포지토리는 Phase 1과 동일하게 SQLite 고정, `data/sampleorder.db`의
  새 테이블(`production_queue`)을 사용한다.
- 컨트롤러/레포지토리 테스트는 실제 SQLite(`tmp_path`)를 쓰고 view만 기록용
  페이크로 대체한다 (mock 금지). `run()`의 메뉴 루프는 테스트하지 않는다.
- 이 프로젝트는 리뷰어 서브에이전트를 쓰지 않는다: 계획 확정 → 구현 → 테스트
  통과 확인 → 커밋 순으로 진행한다.

---

### Task 1: `ProductionJob` 모델 + SQLite 큐 Repository

**Files:**
- Create: `model/production_job.py`
- Create: `model/production_queue_repository.py`
- Test: `test_production_queue_repository.py`

**Interfaces:**
- Consumes: 없음
- Produces: `ProductionJob(id, order_id, shortage_qty, actual_qty, total_time, created_at)`,
  `ProductionQueueRepository`(ABC): `enqueue(job) -> ProductionJob`,
  `list_pending() -> list[ProductionJob]` (삽입 순서 = FIFO 순서).
  `SqliteProductionQueueRepository(path: str = "data/sampleorder.db")`.
  Task 2(`ApprovalController`)와 Phase 5(생산 라인 스레드)가 그대로 사용한다.

- [ ] **Step 1: `model/production_job.py` 작성**

```python
from dataclasses import dataclass


@dataclass
class ProductionJob:
    id: int | None
    order_id: int
    shortage_qty: int
    actual_qty: int
    total_time: float
    created_at: str | None
```

- [ ] **Step 2: `model/production_queue_repository.py`에 ABC 작성**

```python
from abc import ABC, abstractmethod

from model.production_job import ProductionJob


class ProductionQueueRepository(ABC):
    @abstractmethod
    def enqueue(self, job: ProductionJob) -> ProductionJob:
        ...

    @abstractmethod
    def list_pending(self) -> list[ProductionJob]:
        ...
```

- [ ] **Step 3: 실패하는 테스트 작성 — `test_production_queue_repository.py`**

```python
from model.production_job import ProductionJob
from model.production_queue_repository import SqliteProductionQueueRepository


def _repo(tmp_path):
    return SqliteProductionQueueRepository(str(tmp_path / "test.db"))


def _job(order_id, shortage_qty=10, actual_qty=11, total_time=5.5):
    return ProductionJob(
        id=None, order_id=order_id, shortage_qty=shortage_qty,
        actual_qty=actual_qty, total_time=total_time, created_at=None,
    )


def test_enqueue_assigns_id_and_created_at(tmp_path):
    repo = _repo(tmp_path)
    job = repo.enqueue(_job(order_id=1))
    assert job.id == 1
    assert job.created_at is not None


def test_list_pending_returns_jobs_in_fifo_order(tmp_path):
    repo = _repo(tmp_path)
    first = repo.enqueue(_job(order_id=1))
    second = repo.enqueue(_job(order_id=2))
    third = repo.enqueue(_job(order_id=3))

    pending = repo.list_pending()

    assert [job.order_id for job in pending] == [1, 2, 3]
    assert [job.id for job in pending] == [first.id, second.id, third.id]


def test_list_pending_preserves_job_fields(tmp_path):
    repo = _repo(tmp_path)
    repo.enqueue(_job(order_id=5, shortage_qty=20, actual_qty=22, total_time=11.0))

    pending = repo.list_pending()

    assert pending[0].shortage_qty == 20
    assert pending[0].actual_qty == 22
    assert pending[0].total_time == 11.0
```

- [ ] **Step 4: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_production_queue_repository.py -v`
Expected: `ImportError: cannot import name 'SqliteProductionQueueRepository'` 로 전부 실패.

- [ ] **Step 5: `SqliteProductionQueueRepository` 구현**

`model/production_queue_repository.py`에 이어서 추가:

```python
import os
import sqlite3
from datetime import datetime

# (ProductionQueueRepository ABC는 Step 2에서 이미 작성됨, 아래를 같은 파일 하단에 추가)


class SqliteProductionQueueRepository(ProductionQueueRepository):
    def __init__(self, path: str = "data/sampleorder.db") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS production_queue ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "order_id INTEGER NOT NULL,"
            "shortage_qty INTEGER NOT NULL,"
            "actual_qty INTEGER NOT NULL,"
            "total_time REAL NOT NULL,"
            "created_at TEXT NOT NULL)"
        )
        self._conn.commit()

    def enqueue(self, job: ProductionJob) -> ProductionJob:
        job.created_at = datetime.now().isoformat(timespec="seconds")
        cursor = self._conn.execute(
            "INSERT INTO production_queue (order_id, shortage_qty, actual_qty, total_time, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (job.order_id, job.shortage_qty, job.actual_qty, job.total_time, job.created_at),
        )
        self._conn.commit()
        job.id = cursor.lastrowid
        return job

    def list_pending(self) -> list[ProductionJob]:
        rows = self._conn.execute(
            "SELECT id, order_id, shortage_qty, actual_qty, total_time, created_at "
            "FROM production_queue ORDER BY id ASC"
        ).fetchall()
        return [ProductionJob(*row) for row in rows]
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_production_queue_repository.py -v`
Expected: 3개 테스트 모두 `PASSED`.

- [ ] **Step 7: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add model/production_job.py model/production_queue_repository.py test_production_queue_repository.py
git commit -m "feat: add ProductionJob model and SQLite queue repository"
```

---

### Task 2: `ApprovalController` + 콘솔 뷰 확장

**Files:**
- Modify: `view/console_view.py` (함수 추가, 기존 함수는 그대로 유지)
- Create: `controller/approval_controller.py`
- Test: `test_approval_controller.py`

**Interfaces:**
- Consumes: `model.order.OrderStatus`, `model.order_repository.SqliteOrderRepository`,
  `model.sample_repository.SqliteSampleRepository`,
  `model.production_job.ProductionJob`,
  `model.production_queue_repository.SqliteProductionQueueRepository` (Task 1),
  `model.sample_id_format.format_sample_id` (Phase 2)
- Produces: `ApprovalController(order_repository, sample_repository, production_queue_repository, view) -> None`,
  공개 메서드 `run()`. `view` 프로토콜에 다음 함수가 필요:
  `prompt_approval_menu() -> str`, `show_order_list(orders: list[Order]) -> None`,
  `prompt_order_selection(count: int) -> int | None`,
  `prompt_approval_decision() -> str`, `show_message(msg: str) -> None`,
  `show_error(msg: str) -> None` (뒤 두 개는 이미 존재).

- [ ] **Step 1: `view/console_view.py`에 승인/거절 메뉴 함수 추가**

파일 끝에 이어서 추가:

```python
APPROVAL_MENU_TEXT = """
1. 주문 승인/거절
0. 뒤로
"""


def prompt_approval_menu() -> str:
    print(APPROVAL_MENU_TEXT)
    return input("선택 > ")


def show_order_list(orders: list) -> None:
    for idx, order in enumerate(orders, start=1):
        print(
            f"[{idx}] {order.order_no} | 시료 {format_sample_id(order.sample_id)} "
            f"| 고객 {order.customer_name} | 수량 {order.qty}ea | 상태 {order.status.value}"
        )


def prompt_order_selection(count: int) -> int | None:
    raw = input(f"승인/거절할 번호 (1-{count}) > ")
    try:
        return int(raw)
    except ValueError:
        return None


def prompt_approval_decision() -> str:
    return input("[Y] 승인  [N] 거절 > ")
```

- [ ] **Step 2: 실패하는 테스트 작성 — `test_approval_controller.py`**

```python
import math

from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.order import Order, OrderStatus
from model.order_repository import SqliteOrderRepository
from model.production_queue_repository import SqliteProductionQueueRepository
from controller.approval_controller import ApprovalController


class _FakeView:
    def __init__(self, selection=None, decision=None):
        self.messages = []
        self.errors = []
        self.shown_orders = None
        self._selection = selection
        self._decision = decision

    def show_order_list(self, orders):
        self.shown_orders = orders

    def prompt_order_selection(self, count):
        return self._selection

    def prompt_approval_decision(self):
        return self._decision

    def show_message(self, msg):
        self.messages.append(msg)

    def show_error(self, msg):
        self.errors.append(msg)


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path), SqliteProductionQueueRepository(path)


def _reserved_order(order_repo, sample_id, qty, customer_name="SK하이닉스"):
    return order_repo.add(
        Order(id=None, order_no=None, sample_id=sample_id, customer_name=customer_name,
              qty=qty, status=OrderStatus.RESERVED, created_at=None)
    )


def test_process_approval_confirms_order_when_stock_is_sufficient(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.5, yield_rate=0.9, stock_qty=100))
    order = _reserved_order(order_repo, sample.id, qty=50)
    view = _FakeView(selection=1, decision="Y")
    controller = ApprovalController(order_repo, sample_repo, queue_repo, view)

    controller._process_approval()

    updated_order = order_repo.get(order.id)
    updated_sample = sample_repo.get(sample.id)
    assert updated_order.status == OrderStatus.CONFIRMED
    assert updated_sample.stock_qty == 50
    assert queue_repo.list_pending() == []
    assert len(view.messages) == 1


def test_process_approval_enqueues_production_when_stock_is_insufficient(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.5, yield_rate=0.8, stock_qty=30))
    order = _reserved_order(order_repo, sample.id, qty=80)
    view = _FakeView(selection=1, decision="Y")
    controller = ApprovalController(order_repo, sample_repo, queue_repo, view)

    controller._process_approval()

    updated_order = order_repo.get(order.id)
    updated_sample = sample_repo.get(sample.id)
    pending = queue_repo.list_pending()
    assert updated_order.status == OrderStatus.PRODUCING
    assert updated_sample.stock_qty == 30
    assert len(pending) == 1
    assert pending[0].order_id == order.id
    assert pending[0].shortage_qty == 50
    assert pending[0].actual_qty == math.ceil(50 / 0.8)
    assert pending[0].total_time == 0.5 * math.ceil(50 / 0.8)


def test_process_approval_rejects_order_on_n_decision(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.5, yield_rate=0.9, stock_qty=100))
    order = _reserved_order(order_repo, sample.id, qty=50)
    view = _FakeView(selection=1, decision="N")
    controller = ApprovalController(order_repo, sample_repo, queue_repo, view)

    controller._process_approval()

    updated_order = order_repo.get(order.id)
    updated_sample = sample_repo.get(sample.id)
    assert updated_order.status == OrderStatus.REJECTED
    assert updated_sample.stock_qty == 100
    assert queue_repo.list_pending() == []


def test_process_approval_shows_message_when_no_reserved_orders(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    view = _FakeView()
    controller = ApprovalController(order_repo, sample_repo, queue_repo, view)

    controller._process_approval()

    assert view.messages == ["대기 중인 주문이 없습니다."]


def test_process_approval_rejects_invalid_selection_number(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.5, yield_rate=0.9, stock_qty=100))
    order = _reserved_order(order_repo, sample.id, qty=50)
    view = _FakeView(selection=5, decision="Y")
    controller = ApprovalController(order_repo, sample_repo, queue_repo, view)

    controller._process_approval()

    assert view.errors == ["잘못된 번호입니다."]
    assert order_repo.get(order.id).status == OrderStatus.RESERVED


def test_process_approval_rejects_invalid_decision_letter(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.5, yield_rate=0.9, stock_qty=100))
    order = _reserved_order(order_repo, sample.id, qty=50)
    view = _FakeView(selection=1, decision="X")
    controller = ApprovalController(order_repo, sample_repo, queue_repo, view)

    controller._process_approval()

    assert view.errors == ["Y 또는 N을 입력해야 합니다."]
    assert order_repo.get(order.id).status == OrderStatus.RESERVED
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_approval_controller.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.approval_controller'` 로 전부 실패.

- [ ] **Step 4: `controller/approval_controller.py` 구현**

```python
import math

from model.order import OrderStatus
from model.production_job import ProductionJob

EXIT_CHOICE = "0"


class ApprovalController:
    def __init__(self, order_repository, sample_repository, production_queue_repository, view) -> None:
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._production_queue_repository = production_queue_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_approval_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._process_approval()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _process_approval(self) -> None:
        reserved_orders = self._order_repository.list_by_status(OrderStatus.RESERVED)
        if not reserved_orders:
            self._view.show_message("대기 중인 주문이 없습니다.")
            return

        self._view.show_order_list(reserved_orders)
        selection = self._view.prompt_order_selection(len(reserved_orders))
        if not isinstance(selection, int) or not (1 <= selection <= len(reserved_orders)):
            self._view.show_error("잘못된 번호입니다.")
            return
        order = reserved_orders[selection - 1]

        decision = self._view.prompt_approval_decision().strip().upper()
        if decision == "Y":
            self._approve(order)
        elif decision == "N":
            self._reject(order)
        else:
            self._view.show_error("Y 또는 N을 입력해야 합니다.")

    def _approve(self, order) -> None:
        sample = self._sample_repository.get(order.sample_id)
        if sample.stock_qty >= order.qty:
            self._sample_repository.update_stock(sample.id, -order.qty)
            updated = self._order_repository.update_status(order.id, OrderStatus.CONFIRMED)
            self._view.show_message(f"승인 완료: {updated.order_no} (상태: {updated.status.value})")
            return

        shortage = order.qty - sample.stock_qty
        actual_qty = math.ceil(shortage / sample.yield_rate)
        total_time = sample.avg_production_time * actual_qty
        self._production_queue_repository.enqueue(
            ProductionJob(
                id=None,
                order_id=order.id,
                shortage_qty=shortage,
                actual_qty=actual_qty,
                total_time=total_time,
                created_at=None,
            )
        )
        updated = self._order_repository.update_status(order.id, OrderStatus.PRODUCING)
        self._view.show_message(
            f"재고 부족으로 생산 등록: {updated.order_no} (상태: {updated.status.value}, "
            f"실생산량 {actual_qty}ea, 예상 생산시간 {total_time:.1f}min)"
        )

    def _reject(self, order) -> None:
        updated = self._order_repository.update_status(order.id, OrderStatus.REJECTED)
        self._view.show_message(f"거절 처리: {updated.order_no} (상태: {updated.status.value})")
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_approval_controller.py -v`
Expected: 7개 테스트 모두 `PASSED`.

- [ ] **Step 6: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add view/console_view.py controller/approval_controller.py test_approval_controller.py
git commit -m "feat: add ApprovalController for order approve/reject"
```

---

### Task 3: 단독 실행 진입점 `approval_menu.py`

**Files:**
- Create: `approval_menu.py`

**Interfaces:**
- Consumes: `controller.approval_controller.ApprovalController`,
  `model.order_repository.SqliteOrderRepository`,
  `model.sample_repository.SqliteSampleRepository`,
  `model.production_queue_repository.SqliteProductionQueueRepository`,
  `view.console_view`
- Produces: 없음 (Phase 8에서 통합 `main.py`가 이 컨트롤러를 메뉴 중 하나로 흡수)

- [ ] **Step 1: `approval_menu.py` 작성**

```python
from controller.approval_controller import ApprovalController
from model.order_repository import SqliteOrderRepository
from model.production_queue_repository import SqliteProductionQueueRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    ApprovalController(
        SqliteOrderRepository(), SqliteSampleRepository(), SqliteProductionQueueRepository(), console_view
    ).run()
```

- [ ] **Step 2: 수동 스모크 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -c "import ast; ast.parse(open('approval_menu.py', encoding='utf-8').read())"`
Expected: 에러 없이 종료.

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add approval_menu.py
git commit -m "feat: add standalone approval_menu.py entrypoint"
```

---

### Task 4: 전체 검증 및 푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 38개(Phase 1~3) + 신규(`test_production_queue_repository.py` 3개 +
`test_approval_controller.py` 7개) = 총 48개 모두 `PASSED`.

- [ ] **Step 2: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
