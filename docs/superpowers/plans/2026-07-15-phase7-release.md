# Phase 7 — 출고 처리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or plain inline execution) to implement this plan task-by-task. No reviewer subagent is dispatched for this project — see project feedback memory. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `CONFIRMED` 상태 주문에 대해 출고를 실행하는 `ReleaseController`를
추가한다. 주문 상태를 `RELEASED`로 전환한다(PRD 11장).

**Architecture:** Phase 4(`ApprovalController`)에서 만든 "목록 표시 → 번호
선택" 상호작용과 `show_order_list`/`prompt_order_selection` 뷰 함수를 그대로
재사용한다. Phase 4/5의 재고 정합성 수정 이후 `CONFIRMED` 상태에 도달한
주문은 이미 승인 시점(재고 충분) 또는 생산 완료 시점(재고 부족)에 재고가
정산 완료된 상태이므로, 출고 처리는 **재고를 다시 건드리지 않고 주문 상태만
전환**한다. 따라서 `ReleaseController`는 `sample_repository` 없이
`order_repository`와 `view`만 있으면 된다.

**Tech Stack:** Python 3.13, pytest. 신규 SQL 스키마 변경 없음.

## Global Constraints

- 출고 대상은 `CONFIRMED` 상태 주문만 나열한다(`order_repository.list_by_status(OrderStatus.CONFIRMED)`).
- 출고 처리는 재고를 차감/가산하지 않는다 — `CONFIRMED` 도달 시점에 이미
  재고가 정산되어 있다(승인 시 즉시 차감, 또는 생산 완료 시
  `actual_qty - qty`로 차감, Phase 4/5에서 이미 구현됨).
- 선택 방식은 Phase 4와 동일: 방금 표시한 `CONFIRMED` 목록의 1부터 시작하는
  번호로 받는다. 범위를 벗어나거나 숫자가 아니면 에러 처리하고 아무 것도
  바꾸지 않는다.
- `view.show_order_list`, `view.prompt_order_selection`(Phase 4 산출물)을
  그대로 재사용하고 새로 만들지 않는다.
- 컨트롤러 테스트는 실제 SQLite(`tmp_path`)를 쓰고 view만 기록용 페이크로
  대체한다 (mock 금지). `run()`의 메뉴 루프는 테스트하지 않는다.
- 이 프로젝트는 리뷰어 서브에이전트를 쓰지 않는다: 계획 확정 → 구현 → 테스트
  통과 확인 → 커밋 순으로 진행한다.

---

### Task 1: `ReleaseController` + 콘솔 뷰 확장

**Files:**
- Modify: `view/console_view.py` (메뉴 텍스트/함수 1개만 추가, 기존 함수는
  그대로 유지)
- Create: `controller/release_controller.py`
- Test: `test_release_controller.py`

**Interfaces:**
- Consumes: `model.order.OrderStatus`, `model.order_repository.SqliteOrderRepository`,
  기존 `view.show_order_list`/`view.prompt_order_selection`(Phase 4 산출물)
- Produces: `ReleaseController(order_repository, view) -> None`, 공개 메서드
  `run()`. `view` 프로토콜에 다음 함수가 필요: `prompt_release_menu() -> str`
  (신규), `show_order_list`, `prompt_order_selection`, `show_message`,
  `show_error` (모두 이미 존재).

- [ ] **Step 1: `view/console_view.py`에 출고 메뉴 함수 추가**

파일 끝에 이어서 추가:

```python
RELEASE_MENU_TEXT = """
1. 출고 처리
0. 뒤로
"""


def prompt_release_menu() -> str:
    print(RELEASE_MENU_TEXT)
    return input("선택 > ")
```

- [ ] **Step 2: 실패하는 테스트 작성 — `test_release_controller.py`**

```python
from model.order import Order, OrderStatus
from model.order_repository import SqliteOrderRepository
from controller.release_controller import ReleaseController


class _FakeView:
    def __init__(self, selection=None):
        self.messages = []
        self.errors = []
        self.shown_orders = None
        self._selection = selection

    def show_order_list(self, orders):
        self.shown_orders = orders

    def prompt_order_selection(self, count):
        return self._selection

    def show_message(self, msg):
        self.messages.append(msg)

    def show_error(self, msg):
        self.errors.append(msg)


def _repo(tmp_path):
    return SqliteOrderRepository(str(tmp_path / "test.db"))


def _confirmed_order(order_repo, sample_id=1, qty=50, customer_name="SK하이닉스"):
    order = order_repo.add(
        Order(id=None, order_no=None, sample_id=sample_id, customer_name=customer_name,
              qty=qty, status=OrderStatus.RESERVED, created_at=None)
    )
    return order_repo.update_status(order.id, OrderStatus.CONFIRMED)


def test_process_release_transitions_confirmed_order_to_released(tmp_path):
    order_repo = _repo(tmp_path)
    order = _confirmed_order(order_repo)
    view = _FakeView(selection=1)
    controller = ReleaseController(order_repo, view)

    controller._process_release()

    updated = order_repo.get(order.id)
    assert updated.status == OrderStatus.RELEASED
    assert len(view.messages) == 1
    assert updated.order_no in view.messages[0]


def test_process_release_shows_message_when_no_confirmed_orders(tmp_path):
    order_repo = _repo(tmp_path)
    view = _FakeView()
    controller = ReleaseController(order_repo, view)

    controller._process_release()

    assert view.messages == ["출고 가능한 주문이 없습니다."]


def test_process_release_rejects_invalid_selection_number(tmp_path):
    order_repo = _repo(tmp_path)
    order = _confirmed_order(order_repo)
    view = _FakeView(selection=5)
    controller = ReleaseController(order_repo, view)

    controller._process_release()

    assert view.errors == ["잘못된 번호입니다."]
    assert order_repo.get(order.id).status == OrderStatus.CONFIRMED


def test_process_release_rejects_non_numeric_selection(tmp_path):
    order_repo = _repo(tmp_path)
    order = _confirmed_order(order_repo)
    view = _FakeView(selection=None)
    controller = ReleaseController(order_repo, view)

    controller._process_release()

    assert view.errors == ["잘못된 번호입니다."]
    assert order_repo.get(order.id).status == OrderStatus.CONFIRMED
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_release_controller.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.release_controller'` 로 전부 실패.

- [ ] **Step 4: `controller/release_controller.py` 구현**

```python
from model.order import OrderStatus

EXIT_CHOICE = "0"


class ReleaseController:
    def __init__(self, order_repository, view) -> None:
        self._order_repository = order_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_release_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._process_release()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _process_release(self) -> None:
        confirmed_orders = self._order_repository.list_by_status(OrderStatus.CONFIRMED)
        if not confirmed_orders:
            self._view.show_message("출고 가능한 주문이 없습니다.")
            return

        self._view.show_order_list(confirmed_orders)
        selection = self._view.prompt_order_selection(len(confirmed_orders))
        if not isinstance(selection, int) or not (1 <= selection <= len(confirmed_orders)):
            self._view.show_error("잘못된 번호입니다.")
            return
        order = confirmed_orders[selection - 1]

        updated = self._order_repository.update_status(order.id, OrderStatus.RELEASED)
        self._view.show_message(f"출고 처리 완료: {updated.order_no} (상태: {updated.status.value})")
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_release_controller.py -v`
Expected: 4개 테스트 모두 `PASSED`.

- [ ] **Step 6: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add view/console_view.py controller/release_controller.py test_release_controller.py
git commit -m "feat: add ReleaseController for order shipment"
```

---

### Task 2: 단독 실행 진입점 `release_menu.py`

**Files:**
- Create: `release_menu.py`

**Interfaces:**
- Consumes: `controller.release_controller.ReleaseController`,
  `model.order_repository.SqliteOrderRepository`, `view.console_view`
- Produces: 없음 (Phase 8에서 통합 `main.py`가 이 컨트롤러를 메뉴 중 하나로 흡수)

- [ ] **Step 1: `release_menu.py` 작성**

```python
from controller.release_controller import ReleaseController
from model.order_repository import SqliteOrderRepository
from view import console_view

if __name__ == "__main__":
    ReleaseController(SqliteOrderRepository(), console_view).run()
```

- [ ] **Step 2: 수동 스모크 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -c "import ast; ast.parse(open('release_menu.py', encoding='utf-8').read())"`
Expected: 에러 없이 종료.

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add release_menu.py
git commit -m "feat: add standalone release_menu.py entrypoint"
```

---

### Task 3: 전체 검증 및 푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 60개(Phase 1~6) + 신규 `test_release_controller.py` 4개 =
총 64개 모두 `PASSED`.

- [ ] **Step 2: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
