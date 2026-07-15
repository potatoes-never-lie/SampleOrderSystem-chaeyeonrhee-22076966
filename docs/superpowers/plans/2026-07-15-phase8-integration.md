# Phase 8 — 통합 & 더미데이터/모니터 도구 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or plain inline execution) to implement this plan task-by-task. No reviewer subagent is dispatched for this project — see project feedback memory. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 1~7에서 만든 6개 서브 컨트롤러(시료 관리/시료 주문/승인·거절/
모니터링/생산라인/출고)를 하나의 메인 메뉴(`main.py`)로 통합하고, 남아있던
`Item` 전용 더미데이터 도구(`seed_controller.py`)와 구 스켈레톤
(`model/item.py`, `model/repository.py`)을 Sample/Order 도메인으로 완전히
교체한다. 마지막으로 접수→승인→생산→출고 전체 흐름을 검증하는 엔드투엔드
테스트를 추가한다.

**Architecture:** `MainMenuController`는 요약 정보(등록 시료 수/총 재고/전체
주문 수/생산 대기 건수)를 보여준 뒤 메뉴 선택에 따라 이미 완성된 6개
서브 컨트롤러의 `run()`을 그대로 호출한다(각 서브 컨트롤러는 새로 만들지
않는다). `main.py`는 `ProductionLineWorker`를 시작한 뒤
`MainMenuController.run()`을 실행하고, 종료 시 `finally`에서 워커를
정지한다(`production_line_menu.py`와 동일한 패턴). `SeedController`는
Sample/Order 리포지토리를 받아 더미 시료와 주문(`RESERVED`)을 생성하도록
다시 작성하고, 이제 아무도 참조하지 않게 되는 `model/item.py`/
`model/repository.py`를 삭제한다. 실시간 데이터 조회 도구(`monitor.py`)는
새 `LiveMonitorController`로 Sample/Order 데이터를 주기적으로 출력하도록
다시 만든다.

**Tech Stack:** Python 3.13, pytest. 신규 SQL 스키마 변경 없음.

## Global Constraints

- 메인 메뉴 항목/번호는 PRD 10장 메뉴 표와 매칭한다:
  `[1] 시료 관리, [2] 시료 주문, [3] 주문 승인/거절, [4] 모니터링,
  [5] 생산라인 조회, [6] 출고 처리, [0] 종료`.
- `MainMenuController`는 이미 만들어진 서브 컨트롤러 인스턴스를 주입받아
  `run()`만 호출한다 — 서브 컨트롤러 내부 로직을 다시 구현하지 않는다.
- 더미 시료 이름은 UNIQUE 제약 때문에 인덱스를 포함해 중복 없이 생성한다.
  더미 주문은 항상 실제로 생성된 시료의 id를 참조하고 상태는 `RESERVED`로
  시작한다(그 이후 상태는 콘솔에서 담당자가 승인/생산/출고를 진행하며
  바뀌는 것이 자연스럽다 — 시드 단계에서 임의로 상태를 섞지 않는다).
- `model/item.py`, `model/repository.py`를 참조하는 코드가 더 이상 없는지
  삭제 전에 확인한다(`grep -rn "model.item\|model\.repository" --include="*.py" .`).
- 컨트롤러/시드 테스트는 실제 SQLite(`tmp_path`)를 쓰고 view만 기록용
  페이크로 대체한다 (mock 금지). `run()`의 메뉴 루프는 테스트하지 않는다.
- 이 프로젝트는 리뷰어 서브에이전트를 쓰지 않는다: 계획 확정 → 구현 → 테스트
  통과 확인 → 커밋 순으로 진행한다.

---

### Task 1: `MainMenuController` + 콘솔 뷰 확장

**Files:**
- Modify: `view/console_view.py` (함수 추가, 기존 함수는 그대로 유지)
- Create: `controller/main_menu_controller.py`
- Test: `test_main_menu_controller.py`

**Interfaces:**
- Consumes: 이미 만들어진 6개 서브 컨트롤러(`SampleController`,
  `OrderController`, `ApprovalController`, `MonitoringController`,
  `ProductionLineController`, `ReleaseController`)와 그것들이 필요로 하는
  리포지토리(`sample_repository`, `order_repository`,
  `production_queue_repository`)
- Produces: `MainMenuController(sample_repository, order_repository,
  production_queue_repository, sample_controller, order_controller,
  approval_controller, monitoring_controller, production_line_controller,
  release_controller, view) -> None`, 공개 메서드 `run()`. `view` 프로토콜에
  `prompt_main_menu(summary: dict) -> str`, `show_error(msg: str) -> None`
  (이미 존재)가 필요. Task 2(`main.py`)가 이 클래스를 그대로 사용한다.

- [ ] **Step 1: `view/console_view.py`에 메인 메뉴 함수 추가**

파일 끝에 이어서 추가:

```python
MAIN_MENU_TEXT = """
[1] 시료 관리      [2] 시료 주문
[3] 주문 승인/거절 [4] 모니터링
[5] 생산라인 조회  [6] 출고 처리
[0] 종료
"""


def show_main_summary(summary: dict) -> None:
    print("=" * 60)
    print("반도체 시료 생산주문관리 시스템")
    print(f"등록 시료 {summary['sample_count']}종   총 재고 {summary['total_stock']}ea")
    print(f"전체 주문 {summary['order_count']}건   생산라인 {summary['pending_production']}건 대기")
    print("=" * 60)


def prompt_main_menu(summary: dict) -> str:
    show_main_summary(summary)
    print(MAIN_MENU_TEXT)
    return input("선택 > ")
```

- [ ] **Step 2: 실패하는 테스트 작성 — `test_main_menu_controller.py`**

```python
from model.sample import Sample
from model.order import Order, OrderStatus
from controller.main_menu_controller import MainMenuController


class _FakeRepo:
    def __init__(self, items):
        self._items = items

    def list_all(self):
        return self._items

    def list_pending(self):
        return self._items


class _FakeSubController:
    def __init__(self):
        self.run_count = 0

    def run(self):
        self.run_count += 1


class _ScriptedView:
    def __init__(self, choices):
        self._choices = list(choices)
        self.summaries = []
        self.errors = []

    def prompt_main_menu(self, summary):
        self.summaries.append(summary)
        return self._choices.pop(0)

    def show_error(self, msg):
        self.errors.append(msg)


def _controller(choices, sample_repo=None, order_repo=None, queue_repo=None, **subs):
    view = _ScriptedView(choices)
    controller = MainMenuController(
        sample_repo or _FakeRepo([]),
        order_repo or _FakeRepo([]),
        queue_repo or _FakeRepo([]),
        subs.get("sample_controller", _FakeSubController()),
        subs.get("order_controller", _FakeSubController()),
        subs.get("approval_controller", _FakeSubController()),
        subs.get("monitoring_controller", _FakeSubController()),
        subs.get("production_line_controller", _FakeSubController()),
        subs.get("release_controller", _FakeSubController()),
        view,
    )
    return controller, view


def test_build_summary_aggregates_counts_correctly():
    samples = [
        Sample(id=1, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=10),
        Sample(id=2, name="B", avg_production_time=0.2, yield_rate=0.8, stock_qty=25),
    ]
    orders = [
        Order(id=1, order_no="ORD-1", sample_id=1, customer_name="A", qty=5, status=OrderStatus.RESERVED, created_at="x"),
        Order(id=2, order_no="ORD-2", sample_id=2, customer_name="B", qty=3, status=OrderStatus.CONFIRMED, created_at="x"),
    ]
    pending_jobs = [object()]
    controller, _ = _controller(
        ["0"], sample_repo=_FakeRepo(samples), order_repo=_FakeRepo(orders), queue_repo=_FakeRepo(pending_jobs)
    )

    summary = controller._build_summary()

    assert summary == {"sample_count": 2, "total_stock": 35, "order_count": 2, "pending_production": 1}


def test_run_dispatches_choice_1_to_sample_controller():
    sample_controller = _FakeSubController()
    controller, _ = _controller(["1", "0"], sample_controller=sample_controller)
    controller.run()
    assert sample_controller.run_count == 1


def test_run_dispatches_choice_2_to_order_controller():
    order_controller = _FakeSubController()
    controller, _ = _controller(["2", "0"], order_controller=order_controller)
    controller.run()
    assert order_controller.run_count == 1


def test_run_dispatches_choice_3_to_approval_controller():
    approval_controller = _FakeSubController()
    controller, _ = _controller(["3", "0"], approval_controller=approval_controller)
    controller.run()
    assert approval_controller.run_count == 1


def test_run_dispatches_choice_4_to_monitoring_controller():
    monitoring_controller = _FakeSubController()
    controller, _ = _controller(["4", "0"], monitoring_controller=monitoring_controller)
    controller.run()
    assert monitoring_controller.run_count == 1


def test_run_dispatches_choice_5_to_production_line_controller():
    production_line_controller = _FakeSubController()
    controller, _ = _controller(["5", "0"], production_line_controller=production_line_controller)
    controller.run()
    assert production_line_controller.run_count == 1


def test_run_dispatches_choice_6_to_release_controller():
    release_controller = _FakeSubController()
    controller, _ = _controller(["6", "0"], release_controller=release_controller)
    controller.run()
    assert release_controller.run_count == 1


def test_run_shows_error_for_unknown_choice():
    controller, view = _controller(["9", "0"])
    controller.run()
    assert view.errors == ["Unknown option: 9"]
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_main_menu_controller.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.main_menu_controller'` 로 전부 실패.

- [ ] **Step 4: `controller/main_menu_controller.py` 구현**

```python
EXIT_CHOICE = "0"


class MainMenuController:
    def __init__(
        self,
        sample_repository,
        order_repository,
        production_queue_repository,
        sample_controller,
        order_controller,
        approval_controller,
        monitoring_controller,
        production_line_controller,
        release_controller,
        view,
    ) -> None:
        self._sample_repository = sample_repository
        self._order_repository = order_repository
        self._production_queue_repository = production_queue_repository
        self._sample_controller = sample_controller
        self._order_controller = order_controller
        self._approval_controller = approval_controller
        self._monitoring_controller = monitoring_controller
        self._production_line_controller = production_line_controller
        self._release_controller = release_controller
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_main_menu(self._build_summary())
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._sample_controller.run()
            elif choice == "2":
                self._order_controller.run()
            elif choice == "3":
                self._approval_controller.run()
            elif choice == "4":
                self._monitoring_controller.run()
            elif choice == "5":
                self._production_line_controller.run()
            elif choice == "6":
                self._release_controller.run()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _build_summary(self) -> dict:
        samples = self._sample_repository.list_all()
        return {
            "sample_count": len(samples),
            "total_stock": sum(sample.stock_qty for sample in samples),
            "order_count": len(self._order_repository.list_all()),
            "pending_production": len(self._production_queue_repository.list_pending()),
        }
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_main_menu_controller.py -v`
Expected: 8개 테스트 모두 `PASSED`.

- [ ] **Step 6: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add view/console_view.py controller/main_menu_controller.py test_main_menu_controller.py
git commit -m "feat: add MainMenuController dispatching to sub-controllers"
```

---

### Task 2: 통합 엔트리포인트 `main.py`

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: `controller.main_menu_controller.MainMenuController`,
  6개 서브 컨트롤러, `controller.production_line_worker.ProductionLineWorker`,
  `model.sample_repository.SqliteSampleRepository`,
  `model.order_repository.SqliteOrderRepository`,
  `model.production_queue_repository.SqliteProductionQueueRepository`,
  `view.console_view`
- Produces: 없음 (최종 실행 진입점, 이 저장소의 `python main.py`가 이 파일을 실행)

- [ ] **Step 1: `main.py` 작성**

```python
import os

from controller.approval_controller import ApprovalController
from controller.main_menu_controller import MainMenuController
from controller.monitoring_controller import MonitoringController
from controller.order_controller import OrderController
from controller.production_line_controller import ProductionLineController
from controller.production_line_worker import ProductionLineWorker
from controller.release_controller import ReleaseController
from controller.sample_controller import SampleController
from model.order_repository import SqliteOrderRepository
from model.production_queue_repository import SqliteProductionQueueRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

# PRODUCTION_TIME_SCALE = real seconds per simulated production-minute.
# Default 1.0 = 60x speed-up. Set PRODUCTION_TIME_SCALE=60 for real wall-clock time.
TIME_SCALE = float(os.environ.get("PRODUCTION_TIME_SCALE", "1.0"))

if __name__ == "__main__":
    sample_repository = SqliteSampleRepository()
    order_repository = SqliteOrderRepository()
    queue_repository = SqliteProductionQueueRepository()

    worker = ProductionLineWorker(queue_repository, order_repository, sample_repository, time_scale=TIME_SCALE)
    worker.start()
    try:
        MainMenuController(
            sample_repository,
            order_repository,
            queue_repository,
            SampleController(sample_repository, console_view),
            OrderController(order_repository, sample_repository, console_view),
            ApprovalController(order_repository, sample_repository, queue_repository, console_view),
            MonitoringController(order_repository, sample_repository, console_view),
            ProductionLineController(worker, order_repository, sample_repository, console_view),
            ReleaseController(order_repository, console_view),
            console_view,
        ).run()
    finally:
        worker.stop()
```

- [ ] **Step 2: 수동 스모크 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -c "import ast; ast.parse(open('main.py', encoding='utf-8').read())"`
Expected: 에러 없이 종료.

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add main.py
git commit -m "feat: add unified main.py entrypoint"
```

---

### Task 3: `SeedController`를 Sample/Order 도메인으로 개조, 구 스켈레톤 삭제

**Files:**
- Modify: `controller/seed_controller.py` (전면 재작성)
- Modify: `seed.py` (새 리포지토리로 배선)
- Modify: `test_seed_controller.py` (전면 재작성)
- Delete: `model/item.py`, `model/repository.py` (더 이상 아무도 참조하지 않음)

**Interfaces:**
- Consumes: `model.sample.Sample`, `model.sample_repository.SqliteSampleRepository`,
  `model.order.Order`, `model.order.OrderStatus`,
  `model.order_repository.SqliteOrderRepository`
- Produces: `SeedController(sample_repository, order_repository, view,
  sample_count: int = 10, order_count: int = 20) -> None`, 공개 메서드 `run()`.

- [ ] **Step 1: 삭제 전 참조 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && grep -rn "model.item\|model\.repository" --include="*.py" . | grep -v .venv`
Expected: `controller/seed_controller.py`, `model/repository.py`, `seed.py`,
`test_seed_controller.py` 4곳만 출력(모두 이번 Task에서 재작성/삭제할 파일).

- [ ] **Step 2: 실패하는 테스트로 `test_seed_controller.py` 전면 교체**

```python
from model.sample_repository import SqliteSampleRepository
from model.order_repository import SqliteOrderRepository
from controller.seed_controller import SeedController


class _RecordingView:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def show_message(self, msg: str) -> None:
        self.messages.append(msg)


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path)


def test_run_adds_requested_number_of_samples_and_orders(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    view = _RecordingView()

    SeedController(sample_repo, order_repo, view, sample_count=5, order_count=8).run()

    assert len(sample_repo.list_all()) == 5
    assert len(order_repo.list_all()) == 8


def test_run_reports_seeded_counts(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    view = _RecordingView()

    SeedController(sample_repo, order_repo, view, sample_count=3, order_count=4).run()

    assert view.messages == ["Seeded 3 samples and 4 orders."]


def test_run_with_zero_counts_adds_nothing(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    view = _RecordingView()

    SeedController(sample_repo, order_repo, view, sample_count=0, order_count=0).run()

    assert sample_repo.list_all() == []
    assert order_repo.list_all() == []
    assert view.messages == ["Seeded 0 samples and 0 orders."]


def test_generated_orders_reference_existing_samples(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    view = _RecordingView()

    SeedController(sample_repo, order_repo, view, sample_count=4, order_count=10).run()

    sample_ids = {s.id for s in sample_repo.list_all()}
    assert all(order.sample_id in sample_ids for order in order_repo.list_all())
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_seed_controller.py -v`
Expected: `TypeError: SeedController.__init__() ...` 관련 오류로 전부 실패
(기존 `SeedController`는 `(repository, view, count)` 시그니처라 새 테스트와
맞지 않음).

- [ ] **Step 4: `controller/seed_controller.py` 전면 재작성**

```python
import random

from model.order import Order, OrderStatus
from model.sample import Sample

DEFAULT_SAMPLE_COUNT = 10
DEFAULT_ORDER_COUNT = 20

MATERIALS = ["실리콘", "GaN", "SiC", "포토레지스트", "산화막"]
SAMPLE_TYPES = ["웨이퍼-8인치", "웨이퍼-6인치", "에피택셜-4인치", "파워기판-6인치", "PR7", "SiO2"]
CUSTOMERS = ["SK하이닉스", "삼성전자 파운드리", "LG이노텍", "DB하이텍", "한양대 연구실", "팹리스 A"]


class SeedController:
    def __init__(
        self,
        sample_repository,
        order_repository,
        view,
        sample_count: int = DEFAULT_SAMPLE_COUNT,
        order_count: int = DEFAULT_ORDER_COUNT,
    ) -> None:
        self._sample_repository = sample_repository
        self._order_repository = order_repository
        self._view = view
        self._sample_count = sample_count
        self._order_count = order_count

    def run(self) -> None:
        samples = [self._add_random_sample(i) for i in range(self._sample_count)]
        if samples:
            for _ in range(self._order_count):
                self._add_random_order(samples)
        self._view.show_message(f"Seeded {self._sample_count} samples and {self._order_count} orders.")

    def _add_random_sample(self, index: int) -> Sample:
        name = f"{random.choice(MATERIALS)} {random.choice(SAMPLE_TYPES)} #{index + 1}"
        return self._sample_repository.add(
            Sample(
                id=None,
                name=name,
                avg_production_time=round(random.uniform(0.1, 1.0), 2),
                yield_rate=round(random.uniform(0.7, 0.99), 2),
                stock_qty=random.randint(0, 500),
            )
        )

    def _add_random_order(self, samples: list) -> None:
        sample = random.choice(samples)
        self._order_repository.add(
            Order(
                id=None,
                order_no=None,
                sample_id=sample.id,
                customer_name=random.choice(CUSTOMERS),
                qty=random.randint(1, 300),
                status=OrderStatus.RESERVED,
                created_at=None,
            )
        )
```

- [ ] **Step 5: `seed.py` 새 리포지토리로 배선**

```python
from controller.seed_controller import SeedController
from model.order_repository import SqliteOrderRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    SeedController(SqliteSampleRepository(), SqliteOrderRepository(), console_view).run()
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_seed_controller.py -v`
Expected: 4개 테스트 모두 `PASSED`.

- [ ] **Step 7: 구 스켈레톤 삭제**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git rm model/item.py model/repository.py
```

Run: `python -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('.').rglob('*.py') if '.venv' not in str(p)]"`
Expected: 에러 없이 종료 (남은 코드 중 삭제된 모듈을 import하는 곳이 없음을 재확인).

- [ ] **Step 8: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add controller/seed_controller.py seed.py test_seed_controller.py
git commit -m "refactor: port SeedController to Sample/Order domain, remove Item skeleton

Deletes model/item.py and model/repository.py now that SeedController
(the last remaining caller) has been rewritten to seed Sample/Order
data via the Phase 1 repositories."
```

---

### Task 4: `LiveMonitorController` (실시간 데이터 조회 도구) + `monitor.py`

**Files:**
- Create: `controller/live_monitor_controller.py`
- Test: `test_live_monitor_controller.py`
- Create: `monitor.py`

**Interfaces:**
- Consumes: `model.sample_repository.SqliteSampleRepository`,
  `model.order_repository.SqliteOrderRepository`, 기존
  `view.show_samples`(Phase 2), `view.show_order_list`(Phase 4),
  `view.show_message`/`view.clear_screen`(원래 스켈레톤부터 존재)
- Produces: `LiveMonitorController(sample_repository, order_repository, view,
  interval: float = 2.0) -> None`, 공개 메서드 `run()`. Task 4 자체가 이
  컨트롤러의 유일한 진입점(`monitor.py`)이다. 새 view 함수는 만들지 않는다
  (기존 `show_samples`/`show_order_list`/`show_message`/`clear_screen`을
  재사용).

- [ ] **Step 1: 실패하는 테스트 작성 — `test_live_monitor_controller.py`**

```python
from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.order import Order, OrderStatus
from model.order_repository import SqliteOrderRepository
from controller.live_monitor_controller import LiveMonitorController


class _FakeView:
    def __init__(self):
        self.messages = []
        self.cleared = False
        self.shown_samples = None
        self.shown_orders = None

    def clear_screen(self):
        self.cleared = True

    def show_message(self, msg):
        self.messages.append(msg)

    def show_samples(self, samples):
        self.shown_samples = samples

    def show_order_list(self, orders):
        self.shown_orders = orders


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path)


def test_tick_clears_screen_and_shows_samples_and_orders(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=10))
    order = order_repo.add(
        Order(id=None, order_no=None, sample_id=sample.id, customer_name="B",
              qty=5, status=OrderStatus.RESERVED, created_at=None)
    )
    view = _FakeView()
    controller = LiveMonitorController(sample_repo, order_repo, view)

    controller._tick()

    assert view.cleared is True
    assert view.messages == ["Live data monitor... (Ctrl+C to stop)"]
    assert view.shown_samples == [sample]
    assert view.shown_orders == [order]
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_live_monitor_controller.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.live_monitor_controller'` 로 실패.

- [ ] **Step 3: `controller/live_monitor_controller.py` 구현**

```python
import time


class LiveMonitorController:
    def __init__(self, sample_repository, order_repository, view, interval: float = 2.0) -> None:
        self._sample_repository = sample_repository
        self._order_repository = order_repository
        self._view = view
        self._interval = interval

    def run(self) -> None:
        try:
            while True:
                self._tick()
                time.sleep(self._interval)
        except KeyboardInterrupt:
            self._view.show_message("Monitoring stopped.")

    def _tick(self) -> None:
        self._view.clear_screen()
        self._view.show_message("Live data monitor... (Ctrl+C to stop)")
        self._view.show_samples(self._sample_repository.list_all())
        self._view.show_order_list(self._order_repository.list_all())
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_live_monitor_controller.py -v`
Expected: 1개 테스트 `PASSED`.

- [ ] **Step 5: `monitor.py` 작성**

```python
from controller.live_monitor_controller import LiveMonitorController
from model.order_repository import SqliteOrderRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    LiveMonitorController(SqliteSampleRepository(), SqliteOrderRepository(), console_view, interval=2.0).run()
```

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -c "import ast; ast.parse(open('monitor.py', encoding='utf-8').read())"`
Expected: 에러 없이 종료.

- [ ] **Step 6: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add controller/live_monitor_controller.py test_live_monitor_controller.py monitor.py
git commit -m "feat: add LiveMonitorController and monitor.py for Sample/Order data"
```

---

### Task 5: 엔드투엔드 시나리오 테스트

**Files:**
- Test: `test_end_to_end_order_flow.py`

**Interfaces:**
- Consumes: `SampleController`, `OrderController`, `ApprovalController`,
  `ProductionLineWorker`, `ReleaseController`(모두 이미 완성된 산출물)
- Produces: 없음 (검증 전용 — Phase 1~7의 통합 동작을 하나의 시나리오로 확인)

- [ ] **Step 1: 세 가지 흐름을 검증하는 엔드투엔드 테스트 작성**

```python
from model.sample_repository import SqliteSampleRepository
from model.order_repository import SqliteOrderRepository
from model.production_queue_repository import SqliteProductionQueueRepository
from model.sample import Sample
from model.order import OrderStatus
from controller.sample_controller import SampleController
from controller.order_controller import OrderController
from controller.approval_controller import ApprovalController
from controller.production_line_worker import ProductionLineWorker
from controller.release_controller import ReleaseController


class _ScriptableView:
    def __init__(self):
        self.messages = []
        self.errors = []
        self.sample_input = None
        self.order_input = None
        self.selection = None
        self.decision = None

    def prompt_sample_input(self):
        return self.sample_input

    def prompt_order_input(self):
        return self.order_input

    def prompt_order_selection(self, count):
        return self.selection

    def prompt_approval_decision(self):
        return self.decision

    def show_order_list(self, orders):
        pass

    def show_message(self, msg):
        self.messages.append(msg)

    def show_error(self, msg):
        self.errors.append(msg)


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path), SqliteProductionQueueRepository(path)


def test_full_order_lifecycle_reserve_approve_produce_release(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    view = _ScriptableView()

    view.sample_input = {"name": "실리콘 웨이퍼-8인치", "avg_production_time": "0.1", "yield_rate": "0.8"}
    SampleController(sample_repo, view)._register_sample()
    sample = sample_repo.list_all()[0]
    assert sample.stock_qty == 0

    view.order_input = {"sample_id": f"S-{sample.id:03d}", "customer_name": "SK하이닉스", "qty": "50"}
    OrderController(order_repo, sample_repo, view)._reserve_order()
    order = order_repo.list_all()[0]
    assert order.status == OrderStatus.RESERVED

    view.selection = 1
    view.decision = "Y"
    ApprovalController(order_repo, sample_repo, queue_repo, view)._process_approval()
    order = order_repo.get(order.id)
    assert order.status == OrderStatus.PRODUCING
    assert len(queue_repo.list_pending()) == 1

    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.001)
    assert worker._process_next() is True
    order = order_repo.get(order.id)
    assert order.status == OrderStatus.CONFIRMED

    view.selection = 1
    ReleaseController(order_repo, view)._process_release()
    order = order_repo.get(order.id)
    assert order.status == OrderStatus.RELEASED


def test_full_order_lifecycle_reserve_approve_release_when_stock_sufficient(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    view = _ScriptableView()
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=100))

    view.order_input = {"sample_id": f"S-{sample.id:03d}", "customer_name": "LG이노텍", "qty": "30"}
    OrderController(order_repo, sample_repo, view)._reserve_order()
    order = order_repo.list_all()[0]

    view.selection = 1
    view.decision = "Y"
    ApprovalController(order_repo, sample_repo, queue_repo, view)._process_approval()
    order = order_repo.get(order.id)
    assert order.status == OrderStatus.CONFIRMED
    assert sample_repo.get(sample.id).stock_qty == 70
    assert queue_repo.list_pending() == []

    view.selection = 1
    ReleaseController(order_repo, view)._process_release()
    assert order_repo.get(order.id).status == OrderStatus.RELEASED


def test_full_order_lifecycle_reserve_and_reject(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    view = _ScriptableView()
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=100))

    view.order_input = {"sample_id": f"S-{sample.id:03d}", "customer_name": "DB하이텍", "qty": "10"}
    OrderController(order_repo, sample_repo, view)._reserve_order()
    order = order_repo.list_all()[0]

    view.selection = 1
    view.decision = "N"
    ApprovalController(order_repo, sample_repo, queue_repo, view)._process_approval()

    assert order_repo.get(order.id).status == OrderStatus.REJECTED
    assert sample_repo.get(sample.id).stock_qty == 100
```

- [ ] **Step 2: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_end_to_end_order_flow.py -v`
Expected: 3개 테스트 모두 `PASSED` (새 코드가 아니라 기존 컨트롤러들을
조합만 하므로 실패 없이 바로 통과해야 정상 — 실패하면 앞선 Phase들의
통합 지점에 문제가 있다는 뜻).

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add test_end_to_end_order_flow.py
git commit -m "test: add end-to-end reserve-approve-produce-release scenario"
```

---

### Task 6: 전체 검증 및 푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 64개(Phase 1~7, 단 `test_seed_controller.py`의 옛 3개는
Task 3에서 신규 4개로 교체되어 순증감 +1) + 신규(`test_main_menu_controller.py`
8개 + `test_live_monitor_controller.py` 1개 + `test_end_to_end_order_flow.py`
3개) = 총 77개 모두 `PASSED`.

- [ ] **Step 2: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
