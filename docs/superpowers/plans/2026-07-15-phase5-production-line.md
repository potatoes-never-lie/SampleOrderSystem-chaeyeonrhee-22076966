# Phase 5 — 생산 라인 (백그라운드 스레드) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or plain inline execution) to implement this plan task-by-task. No reviewer subagent is dispatched for this project — see project feedback memory. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 4에서 큐에 등록된 생산 작업(`ProductionJob`)을 실제로 처리하는
백그라운드 스레드(`ProductionLineWorker`)와, 현재 생산 현황·대기 큐를
조회하는 `ProductionLineController`를 추가한다. 생산이 끝나면 재고를
가산하고 주문을 `PRODUCING → CONFIRMED`로 전환한다(PRD 10장).

**Architecture:** 단일 생산 라인 + FIFO. `ProductionLineWorker`는 큐에서
작업을 하나씩 꺼내(dequeue) 처리하는 백그라운드 스레드로, 처리 중인 작업의
시작 시각/진행률을 락으로 보호된 상태로 들고 있다가 `ProductionLineController`가
조회할 수 있게 한다. 스레드 로직(무한 루프)과 "작업 하나 처리" 로직을
분리해서, 후자(`_process_next`)는 스레드 없이 동기적으로 직접 테스트한다.
`ProductionQueueRepository`에 `dequeue(job_id)`를 추가해 작업을 큐에서
제거하는 시점을 명확히 한다(처리 시작 시 즉시 dequeue, 완료 후에는 메모리
상의 "현재 작업" 상태만 정리).

**Tech Stack:** Python 3.13 표준 라이브러리 `threading`, `time`, `math`
(이미 사용 중), pytest.

## 생산 시간 축소 배율(time_scale) — 확정

PRD의 "총 생산 시간"은 분(min) 단위다 (예: 실생산량 54ea × 평균생산시간
0.92min/ea ≈ 49min). 콘솔 데모/테스트에서 실제 49분을 그대로 기다릴 수는
없으므로, `ProductionLineWorker`에 **`time_scale`**(시뮬레이션 1"분"당 실제
대기 초)이라는 보정 계수를 둔다. 기본값은 `time_scale=1.0`(1 시뮬레이션분 =
실제 1초, 60배 가속)으로 확정했다 — 예시 데이터 기준 최대 수십 초 정도면
생산이 끝나서 데모하기에 적당하다. **실제 시간 그대로 흐르게 하려면
`time_scale=60`**(1분 = 실제 60초)을 주면 된다. 테스트에서는 이 값을 아주
작게 주거나 `total_time`이 작은 더미 데이터를 써서 순식간에 끝나게 한다.

코드를 고치지 않고 배율을 바꿀 수 있도록, `production_line_menu.py`
진입점(Task 4)은 이 값을 `PRODUCTION_TIME_SCALE` 환경변수로 오버라이드할 수
있게 한다 (기본값 `1.0`, 예: `PRODUCTION_TIME_SCALE=60 python production_line_menu.py`
로 실행하면 실제 시간 그대로 흐름). Phase 8에서 통합 `main.py`를 만들 때도
같은 환경변수를 그대로 존중한다.

## Global Constraints

- 실 생산량/총 생산 시간 공식은 Phase 4에서 이미 계산되어 `ProductionJob`에
  들어있다 (`shortage_qty`, `actual_qty`, `total_time`) — 이번 Phase는 그 값을
  그대로 소비한다.
- 생산 완료 시: 주문 상태 `PRODUCING → CONFIRMED`, 해당 시료 재고에
  `actual_qty`만큼 가산 (`sample_repository.update_stock(sample_id, +actual_qty)`).
  주문의 `sample_id`는 `order_repository.get(job.order_id)`로 조회한다.
  (참고: 이 시점에는 Phase 4의 승인 로직과 달리 재고가 부족했던 상태이므로
  가산만 하면 되고, 별도 차감 로직은 필요 없다.)
- 큐 처리는 FIFO(`list_pending()`이 이미 삽입 순서로 반환) 순서를 그대로 따른다.
- 작업 처리 시작 시 즉시 `dequeue`하여 큐 테이블에서 제거하고, 진행 중 상태는
  `ProductionLineWorker` 내부 메모리(락으로 보호)에만 둔다 — 앱이 재시작되면
  진행 중이던 작업의 진행률 표시는 초기화된다(영속화하지 않음, 이 과제
  범위에서는 충분).
- 컨트롤러/워커 테스트는 실제 SQLite(`tmp_path`)를 쓰고 view만 기록용
  페이크로 대체한다 (mock 금지). 단, 백그라운드 스레드 자체(`start`/`stop`)를
  검증하는 테스트 1개는 실제 `threading.Thread`와 짧은 `time.sleep`을 사용한다
  (동시성 로직은 실제로 동작을 관찰해야 의미가 있음).
- `run()`의 메뉴 루프는 테스트하지 않는다 (기존 관례).
- 이 프로젝트는 리뷰어 서브에이전트를 쓰지 않는다: 계획 확정 → 구현 → 테스트
  통과 확인 → 커밋 순으로 진행한다.

---

### Task 1: `ProductionQueueRepository`에 `dequeue` 추가

**Files:**
- Modify: `model/production_queue_repository.py` (`dequeue` 메서드 추가)
- Modify: `test_production_queue_repository.py` (테스트 추가)

**Interfaces:**
- Consumes: 없음
- Produces: `ProductionQueueRepository.dequeue(job_id: int) -> None` (존재하지
  않는 `job_id`면 `KeyError`, 기존 `OrderRepository.update_status`/
  `SampleRepository.update`와 동일한 관례). Task 2(`ProductionLineWorker`)가
  작업 처리 시작 시 이 메서드로 큐에서 제거한다.

- [ ] **Step 1: 실패하는 테스트 추가 — `test_production_queue_repository.py`에 이어서 작성**

```python
import pytest


def test_dequeue_removes_job_from_pending(tmp_path):
    repo = _repo(tmp_path)
    job = repo.enqueue(_job(order_id=1))
    repo.enqueue(_job(order_id=2))

    repo.dequeue(job.id)

    assert [j.order_id for j in repo.list_pending()] == [2]


def test_dequeue_raises_for_unknown_job(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(KeyError):
        repo.dequeue(999)
```

(파일 맨 위 `import pytest`가 없다면 추가한다.)

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_production_queue_repository.py -v`
Expected: 새로 추가한 2개가 `FAILED`(`AttributeError: 'SqliteProductionQueueRepository' object has no attribute 'dequeue'`), 기존 3개는 `PASSED`.

- [ ] **Step 3: `dequeue` 구현**

`model/production_queue_repository.py`의 `ProductionQueueRepository` ABC에 추가:

```python
    @abstractmethod
    def dequeue(self, job_id: int) -> None:
        ...
```

`SqliteProductionQueueRepository`에 추가:

```python
    def dequeue(self, job_id: int) -> None:
        cursor = self._conn.execute("DELETE FROM production_queue WHERE id = ?", (job_id,))
        self._conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(job_id)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_production_queue_repository.py -v`
Expected: 5개 테스트 모두 `PASSED`.

- [ ] **Step 5: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add model/production_queue_repository.py test_production_queue_repository.py
git commit -m "feat: add dequeue to ProductionQueueRepository"
```

---

### Task 2: `ProductionLineWorker` (백그라운드 스레드)

**Files:**
- Create: `controller/production_line_worker.py`
- Test: `test_production_line_worker.py`

**Interfaces:**
- Consumes: `model.production_queue_repository.SqliteProductionQueueRepository`,
  `model.order_repository.SqliteOrderRepository`,
  `model.sample_repository.SqliteSampleRepository`, `model.order.OrderStatus`
- Produces:
  `ProductionLineWorker(production_queue_repository, order_repository, sample_repository, time_scale: float = 1.0, poll_interval: float = 0.2)`
  - `start() -> None` / `stop() -> None` — 백그라운드 스레드 시작/정지
  - `_process_next() -> bool` — 큐에서 작업 하나를 꺼내 동기적으로 처리
    (테스트가 스레드 없이 직접 호출), 처리한 게 없으면 `False`
  - `current_status() -> dict | None` — 현재 처리 중인 작업이 있으면
    `{"job": ProductionJob, "progress": float}` (0.0~1.0), 없으면 `None`
  - `list_pending() -> list[ProductionJob]` — 대기 중인 작업 목록(현재 처리
    중인 작업은 이미 dequeue되어 포함되지 않음)
  - Task 3(`ProductionLineController`)가 이 네 메서드를 그대로 사용한다.

- [ ] **Step 1: 실패하는 테스트 작성 — `test_production_line_worker.py`**

```python
import time

from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.order import Order, OrderStatus
from model.order_repository import SqliteOrderRepository
from model.production_job import ProductionJob
from model.production_queue_repository import SqliteProductionQueueRepository
from controller.production_line_worker import ProductionLineWorker


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path), SqliteProductionQueueRepository(path)


def _producing_order(order_repo, sample_id, qty=50):
    order = order_repo.add(
        Order(id=None, order_no=None, sample_id=sample_id, customer_name="SK하이닉스",
              qty=qty, status=OrderStatus.RESERVED, created_at=None)
    )
    return order_repo.update_status(order.id, OrderStatus.PRODUCING)


def test_process_next_returns_false_when_queue_empty(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.0)

    assert worker._process_next() is False


def test_process_next_completes_job_and_updates_order_and_stock(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.5, yield_rate=0.8, stock_qty=30))
    order = _producing_order(order_repo, sample.id, qty=80)
    queue_repo.enqueue(
        ProductionJob(id=None, order_id=order.id, shortage_qty=50, actual_qty=63, total_time=0.01, created_at=None)
    )
    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.01)

    processed = worker._process_next()

    assert processed is True
    updated_order = order_repo.get(order.id)
    updated_sample = sample_repo.get(sample.id)
    assert updated_order.status == OrderStatus.CONFIRMED
    assert updated_sample.stock_qty == 30 + 63
    assert queue_repo.list_pending() == []
    assert worker.current_status() is None


def test_process_next_processes_jobs_in_fifo_order(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    first_order = _producing_order(order_repo, sample.id, qty=10)
    second_order = _producing_order(order_repo, sample.id, qty=10)
    queue_repo.enqueue(ProductionJob(id=None, order_id=first_order.id, shortage_qty=10, actual_qty=12, total_time=0.01, created_at=None))
    queue_repo.enqueue(ProductionJob(id=None, order_id=second_order.id, shortage_qty=10, actual_qty=12, total_time=0.01, created_at=None))
    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.01)

    worker._process_next()

    assert order_repo.get(first_order.id).status == OrderStatus.CONFIRMED
    assert order_repo.get(second_order.id).status == OrderStatus.PRODUCING
    assert [j.order_id for j in worker.list_pending()] == [second_order.id]


def test_start_and_stop_processes_queued_job_in_background(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    order = _producing_order(order_repo, sample.id, qty=10)
    queue_repo.enqueue(
        ProductionJob(id=None, order_id=order.id, shortage_qty=10, actual_qty=12, total_time=1.0, created_at=None)
    )
    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.05, poll_interval=0.02)

    worker.start()
    time.sleep(0.03)
    status = worker.current_status()
    assert status is not None
    assert status["job"].order_id == order.id
    assert 0.0 <= status["progress"] <= 1.0

    deadline = time.monotonic() + 2.0
    while order_repo.get(order.id).status != OrderStatus.CONFIRMED and time.monotonic() < deadline:
        time.sleep(0.02)
    worker.stop()

    assert order_repo.get(order.id).status == OrderStatus.CONFIRMED
    assert sample_repo.get(sample.id).stock_qty == 12
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_production_line_worker.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.production_line_worker'` 로 전부 실패.

- [ ] **Step 3: `controller/production_line_worker.py` 구현**

```python
import threading
import time

from model.order import OrderStatus


class ProductionLineWorker:
    def __init__(
        self,
        production_queue_repository,
        order_repository,
        sample_repository,
        time_scale: float = 1.0,  # ponytail: real seconds per simulated production-minute, tune for demo speed
        poll_interval: float = 0.2,
    ) -> None:
        self._queue_repository = production_queue_repository
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._time_scale = time_scale
        self._poll_interval = poll_interval
        self._lock = threading.Lock()
        self._current = None
        self._stop_event = threading.Event()
        self._thread = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._process_next():
                time.sleep(self._poll_interval)

    def _process_next(self) -> bool:
        pending = self._queue_repository.list_pending()
        if not pending:
            return False
        job = pending[0]
        self._queue_repository.dequeue(job.id)
        with self._lock:
            self._current = {"job": job, "started_at": time.monotonic()}
        time.sleep(job.total_time * self._time_scale)
        self._complete(job)
        with self._lock:
            self._current = None
        return True

    def _complete(self, job) -> None:
        order = self._order_repository.get(job.order_id)
        self._sample_repository.update_stock(order.sample_id, job.actual_qty)
        self._order_repository.update_status(job.order_id, OrderStatus.CONFIRMED)

    def current_status(self) -> dict | None:
        with self._lock:
            if self._current is None:
                return None
            job = self._current["job"]
            elapsed = time.monotonic() - self._current["started_at"]
            total = job.total_time * self._time_scale
            progress = min(elapsed / total, 1.0) if total > 0 else 1.0
            return {"job": job, "progress": progress}

    def list_pending(self):
        return self._queue_repository.list_pending()
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_production_line_worker.py -v`
Expected: 4개 테스트 모두 `PASSED` (마지막 백그라운드 스레드 테스트는 최대 약 2초
소요, 나머지는 즉시 완료).

- [ ] **Step 5: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add controller/production_line_worker.py test_production_line_worker.py
git commit -m "feat: add ProductionLineWorker background thread"
```

---

### Task 3: `ProductionLineController` + 콘솔 뷰 확장

**Files:**
- Modify: `view/console_view.py` (함수 추가, 기존 함수는 그대로 유지)
- Create: `controller/production_line_controller.py`
- Test: `test_production_line_controller.py`

**Interfaces:**
- Consumes: `controller.production_line_worker.ProductionLineWorker`
  (`current_status()`, `list_pending()`), `model.order_repository.SqliteOrderRepository`,
  `model.sample_repository.SqliteSampleRepository`,
  `model.sample_id_format.format_sample_id`
- Produces: `ProductionLineController(worker, order_repository, sample_repository, view) -> None`,
  공개 메서드 `run()`. `view` 프로토콜에 다음 함수가 필요:
  `prompt_production_menu() -> str`,
  `show_production_status(job, order, sample, progress: float) -> None`,
  `show_pending_queue(entries: list[tuple]) -> None`, `show_message(msg: str) -> None`
  (이미 존재).

- [ ] **Step 1: `view/console_view.py`에 생산 라인 메뉴 함수 추가**

파일 끝에 이어서 추가. 생산 현황과 대기 큐를 별도 서브메뉴로 나누지 않고,
"생산 라인 조회" 한 번으로 둘 다 한꺼번에 보여준다 (현재 작업 상태 →
대기 큐 순서로 출력):

```python
PRODUCTION_MENU_TEXT = """
1. 생산 라인 조회
0. 뒤로
"""


def prompt_production_menu() -> str:
    print(PRODUCTION_MENU_TEXT)
    return input("선택 > ")


def show_production_status(job, order, sample, progress: float) -> None:
    print(
        f"주문번호 {order.order_no} | 시료 {format_sample_id(sample.id)} {sample.name} "
        f"| 부족분 {job.shortage_qty}ea → 실생산량 {job.actual_qty}ea "
        f"| 진행률 {progress * 100:.0f}%"
    )


def show_pending_queue(entries: list) -> None:
    if not entries:
        print("(대기 중인 생산 작업 없음)")
        return
    for idx, (job, order) in enumerate(entries, start=1):
        print(
            f"[{idx}] 주문번호 {order.order_no} | 부족분 {job.shortage_qty}ea "
            f"| 실생산량 {job.actual_qty}ea | 예상소요 {job.total_time:.1f}min"
        )
```

- [ ] **Step 2: 실패하는 테스트 작성 — `test_production_line_controller.py`**

```python
from model.production_job import ProductionJob
from model.order import Order, OrderStatus
from model.sample import Sample
from controller.production_line_controller import ProductionLineController


class _FakeWorker:
    def __init__(self, status=None, pending=None):
        self._status = status
        self._pending = pending or []

    def current_status(self):
        return self._status

    def list_pending(self):
        return self._pending


class _FakeRepo:
    def __init__(self, items: dict):
        self._items = items

    def get(self, item_id):
        return self._items.get(item_id)


class _FakeView:
    def __init__(self):
        self.messages = []
        self.status_calls = []
        self.pending_calls = None

    def show_message(self, msg):
        self.messages.append(msg)

    def show_production_status(self, job, order, sample, progress):
        self.status_calls.append((job, order, sample, progress))

    def show_pending_queue(self, entries):
        self.pending_calls = entries


def test_show_status_reports_idle_and_lists_pending_queue():
    order = Order(id=1, order_no="ORD-20260416-0001", sample_id=2, customer_name="A",
                  qty=50, status=OrderStatus.PRODUCING, created_at="2026-04-16T09:00:00")
    job = ProductionJob(id=1, order_id=1, shortage_qty=50, actual_qty=63, total_time=31.5, created_at="2026-04-16T09:00:00")
    worker = _FakeWorker(status=None, pending=[job])
    controller = ProductionLineController(worker, _FakeRepo({1: order}), _FakeRepo({}), _FakeView())

    controller._show_status()

    assert controller._view.messages == ["현재 생산 중인 작업이 없습니다."]
    assert controller._view.status_calls == []
    assert controller._view.pending_calls == [(job, order)]


def test_show_status_reports_current_job_progress_and_pending_queue():
    current_order = Order(id=1, order_no="ORD-20260416-0001", sample_id=2, customer_name="A",
                           qty=50, status=OrderStatus.PRODUCING, created_at="2026-04-16T09:00:00")
    sample = Sample(id=2, name="실리콘 웨이퍼-8인치", avg_production_time=0.5, yield_rate=0.8, stock_qty=30)
    current_job = ProductionJob(id=1, order_id=1, shortage_qty=50, actual_qty=63, total_time=31.5, created_at="2026-04-16T09:00:00")
    pending_order = Order(id=2, order_no="ORD-20260416-0002", sample_id=2, customer_name="B",
                          qty=20, status=OrderStatus.PRODUCING, created_at="2026-04-16T09:05:00")
    pending_job = ProductionJob(id=2, order_id=2, shortage_qty=20, actual_qty=25, total_time=12.5, created_at="2026-04-16T09:05:00")
    worker = _FakeWorker(status={"job": current_job, "progress": 0.4}, pending=[pending_job])
    controller = ProductionLineController(
        worker, _FakeRepo({1: current_order, 2: pending_order}), _FakeRepo({2: sample}), _FakeView()
    )

    controller._show_status()

    assert controller._view.status_calls == [(current_job, current_order, sample, 0.4)]
    assert controller._view.pending_calls == [(pending_job, pending_order)]
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_production_line_controller.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.production_line_controller'` 로 전부 실패.

- [ ] **Step 4: `controller/production_line_controller.py` 구현**

```python
EXIT_CHOICE = "0"


class ProductionLineController:
    def __init__(self, worker, order_repository, sample_repository, view) -> None:
        self._worker = worker
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_production_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._show_status()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _show_status(self) -> None:
        status = self._worker.current_status()
        if status is None:
            self._view.show_message("현재 생산 중인 작업이 없습니다.")
        else:
            job = status["job"]
            order = self._order_repository.get(job.order_id)
            sample = self._sample_repository.get(order.sample_id)
            self._view.show_production_status(job, order, sample, status["progress"])

        entries = [(job, self._order_repository.get(job.order_id)) for job in self._worker.list_pending()]
        self._view.show_pending_queue(entries)
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_production_line_controller.py -v`
Expected: 2개 테스트 모두 `PASSED`.

- [ ] **Step 6: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add view/console_view.py controller/production_line_controller.py test_production_line_controller.py
git commit -m "feat: add ProductionLineController for status/queue display"
```

---

### Task 4: 단독 실행 진입점 `production_line_menu.py`

**Files:**
- Create: `production_line_menu.py`

**Interfaces:**
- Consumes: `controller.production_line_worker.ProductionLineWorker`,
  `controller.production_line_controller.ProductionLineController`,
  `model.order_repository.SqliteOrderRepository`,
  `model.sample_repository.SqliteSampleRepository`,
  `model.production_queue_repository.SqliteProductionQueueRepository`,
  `view.console_view`
- Produces: 없음 (Phase 8에서 통합 `main.py`가 워커 시작/컨트롤러를 흡수).
  `PRODUCTION_TIME_SCALE` 환경변수로 `time_scale`을 오버라이드할 수 있다
  (기본값 `1.0`, `60`을 주면 실제 시간 그대로 흐름).

- [ ] **Step 1: `production_line_menu.py` 작성**

```python
import os

from controller.production_line_controller import ProductionLineController
from controller.production_line_worker import ProductionLineWorker
from model.order_repository import SqliteOrderRepository
from model.production_queue_repository import SqliteProductionQueueRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

# PRODUCTION_TIME_SCALE = real seconds per simulated production-minute.
# Default 1.0 = 60x speed-up (1 simulated minute -> 1 real second), good for demos.
# Set PRODUCTION_TIME_SCALE=60 to run with real wall-clock time (1 minute -> 1 minute).
TIME_SCALE = float(os.environ.get("PRODUCTION_TIME_SCALE", "1.0"))

if __name__ == "__main__":
    order_repository = SqliteOrderRepository()
    sample_repository = SqliteSampleRepository()
    queue_repository = SqliteProductionQueueRepository()

    worker = ProductionLineWorker(queue_repository, order_repository, sample_repository, time_scale=TIME_SCALE)
    worker.start()
    try:
        ProductionLineController(worker, order_repository, sample_repository, console_view).run()
    finally:
        worker.stop()
```

- [ ] **Step 2: 수동 스모크 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -c "import ast; ast.parse(open('production_line_menu.py', encoding='utf-8').read())"`
Expected: 에러 없이 종료.

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add production_line_menu.py
git commit -m "feat: add standalone production_line_menu.py entrypoint"
```

---

### Task 5: 전체 검증 및 푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 47개(Phase 1~4) + 신규(`test_production_queue_repository.py` 2개 +
`test_production_line_worker.py` 4개 + `test_production_line_controller.py` 2개) =
총 55개 모두 `PASSED` (백그라운드 스레드 테스트 때문에 전체 실행 시간이 최대
약 2초 더 걸릴 수 있음).

- [ ] **Step 2: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
