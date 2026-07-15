# Phase 3 — 시료 주문(예약) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or plain inline execution) to implement this plan task-by-task. No reviewer subagent is dispatched for this project — see project feedback memory. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 고객이 요청한 시료를 주문 담당자가 예약(RESERVED) 상태로 접수하는
`OrderController`를 추가한다. Phase 1의 `Order`/`SqliteOrderRepository`,
Phase 2의 `SqliteSampleRepository`/`parse_sample_id`를 그대로 재사용한다.

**Architecture:** `OrderController`는 `order_repository`, `sample_repository`,
`view` 세 개를 주입받는다 — 주문을 만들려면 사용자가 입력한 시료 ID가 실제
등록된 시료인지 `sample_repository.get()`으로 검증해야 하기 때문이다. 시료
ID 입력(`"S-003"` 등)은 Phase 2에서 만든 `parse_sample_id`로 정수 PK로
변환한다. `view/console_view.py`에 주문 메뉴용 입출력 함수를 추가하고, 기존
`sample_menu.py`처럼 단독 실행 진입점 `order_menu.py`도 추가한다.

**Tech Stack:** Python 3.13, pytest. 새 SQL 스키마 변경 없음 (Phase 1 산출물
그대로 사용).

## Global Constraints

- 주문 예약 입력 값은 PRD 7장 그대로: 시료 ID, 고객명, 주문 수량.
- 시료 ID는 `model.sample_id_format.parse_sample_id`로 파싱한다. 파싱 실패
  (`None`) 또는 파싱된 id에 해당하는 시료가 `sample_repository.get()`으로
  조회되지 않으면 에러 처리하고 주문을 만들지 않는다.
- 주문 수량은 정수로 파싱하고 `qty > 0`이어야 한다. 고객명은 공백만 있는
  값을 거부한다 (빈 주문서 방지, 신뢰 경계 입력 검증).
- 주문 생성 시 상태는 항상 `OrderStatus.RESERVED`로 시작한다 (PRD 4장 상태
  흐름: 주문 접수 = RESERVED). `order_no`/`created_at`은 `OrderRepository.add()`가
  자동으로 채운다 (Phase 1에서 이미 구현됨, 이번 Phase에서 변경 없음).
- 컨트롤러 테스트는 실제 SQLite(`tmp_path`)를 쓰고 view만 기록용 페이크로
  대체한다 (레포지토리 mock 금지). `run()`의 메뉴 루프는 테스트하지 않는다
  (Phase 2와 동일한 관례).
- 이 프로젝트는 리뷰어 서브에이전트를 쓰지 않는다: 계획 확정 → 구현 → 테스트
  통과 확인 → 커밋 순으로 진행한다.

---

### Task 1: `OrderController` + 콘솔 뷰 확장

**Files:**
- Modify: `view/console_view.py` (함수 추가, 기존 함수는 그대로 유지)
- Create: `controller/order_controller.py`
- Test: `test_order_controller.py`

**Interfaces:**
- Consumes: `model.order.Order`, `model.order.OrderStatus`,
  `model.order_repository.SqliteOrderRepository` (Phase 1),
  `model.sample_repository.SqliteSampleRepository` (Phase 1/2),
  `model.sample_id_format.parse_sample_id` (Phase 2)
- Produces: `OrderController(order_repository, sample_repository, view) -> None`,
  공개 메서드 `run()`. `view` 프로토콜에 다음 함수가 필요:
  `prompt_order_menu() -> str`, `prompt_order_input() -> dict`,
  `show_message(msg: str) -> None`, `show_error(msg: str) -> None`
  (뒤 두 개는 `console_view.py`에 이미 존재).

- [ ] **Step 1: `view/console_view.py`에 주문 메뉴 함수 추가**

파일 끝에 이어서 추가:

```python
ORDER_MENU_TEXT = """
1. 시료 주문
0. 뒤로
"""


def prompt_order_menu() -> str:
    print(ORDER_MENU_TEXT)
    return input("선택 > ")


def prompt_order_input() -> dict:
    sample_id = input("시료 ID: ")
    customer_name = input("고객명: ")
    qty = input("주문 수량: ")
    return {"sample_id": sample_id, "customer_name": customer_name, "qty": qty}
```

- [ ] **Step 2: 실패하는 테스트 작성 — `test_order_controller.py`**

```python
from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.order_repository import SqliteOrderRepository
from model.order import OrderStatus
from controller.order_controller import OrderController


class _FakeView:
    def __init__(self, order_input=None):
        self.messages = []
        self.errors = []
        self._order_input = order_input

    def prompt_order_input(self):
        return self._order_input

    def show_message(self, msg):
        self.messages.append(msg)

    def show_error(self, msg):
        self.errors.append(msg)


def _sample_repo(tmp_path):
    return SqliteSampleRepository(str(tmp_path / "test.db"))


def _order_repo(tmp_path):
    return SqliteOrderRepository(str(tmp_path / "test.db"))


def _register_sample(sample_repo, name="실리콘 웨이퍼-8인치"):
    return sample_repo.add(Sample(id=None, name=name, avg_production_time=0.5, yield_rate=0.92, stock_qty=100))


def test_reserve_order_creates_reserved_order_for_existing_sample(tmp_path):
    sample_repo = _sample_repo(tmp_path)
    order_repo = _order_repo(tmp_path)
    sample = _register_sample(sample_repo)
    view = _FakeView(order_input={"sample_id": f"S-{sample.id:03d}", "customer_name": "SK하이닉스", "qty": "150"})
    controller = OrderController(order_repo, sample_repo, view)

    controller._reserve_order()

    orders = order_repo.list_all()
    assert len(orders) == 1
    assert orders[0].sample_id == sample.id
    assert orders[0].customer_name == "SK하이닉스"
    assert orders[0].qty == 150
    assert orders[0].status == OrderStatus.RESERVED
    assert len(view.messages) == 1
    assert orders[0].order_no in view.messages[0]


def test_reserve_order_rejects_invalid_sample_id_format(tmp_path):
    sample_repo = _sample_repo(tmp_path)
    order_repo = _order_repo(tmp_path)
    view = _FakeView(order_input={"sample_id": "실리콘", "customer_name": "SK하이닉스", "qty": "150"})
    controller = OrderController(order_repo, sample_repo, view)

    controller._reserve_order()

    assert order_repo.list_all() == []
    assert view.errors == ["유효한 시료 ID 형식이 아닙니다: 실리콘"]


def test_reserve_order_rejects_unknown_sample_id(tmp_path):
    sample_repo = _sample_repo(tmp_path)
    order_repo = _order_repo(tmp_path)
    view = _FakeView(order_input={"sample_id": "S-999", "customer_name": "SK하이닉스", "qty": "150"})
    controller = OrderController(order_repo, sample_repo, view)

    controller._reserve_order()

    assert order_repo.list_all() == []
    assert view.errors == ["존재하지 않는 시료 ID입니다: S-999"]


def test_reserve_order_rejects_non_numeric_qty(tmp_path):
    sample_repo = _sample_repo(tmp_path)
    order_repo = _order_repo(tmp_path)
    sample = _register_sample(sample_repo)
    view = _FakeView(order_input={"sample_id": f"S-{sample.id:03d}", "customer_name": "SK하이닉스", "qty": "많이"})
    controller = OrderController(order_repo, sample_repo, view)

    controller._reserve_order()

    assert order_repo.list_all() == []
    assert view.errors == ["주문 수량은 숫자로 입력해야 합니다."]


def test_reserve_order_rejects_non_positive_qty(tmp_path):
    sample_repo = _sample_repo(tmp_path)
    order_repo = _order_repo(tmp_path)
    sample = _register_sample(sample_repo)
    view = _FakeView(order_input={"sample_id": f"S-{sample.id:03d}", "customer_name": "SK하이닉스", "qty": "0"})
    controller = OrderController(order_repo, sample_repo, view)

    controller._reserve_order()

    assert order_repo.list_all() == []
    assert view.errors == ["주문 수량은 0보다 커야 합니다."]


def test_reserve_order_rejects_blank_customer_name(tmp_path):
    sample_repo = _sample_repo(tmp_path)
    order_repo = _order_repo(tmp_path)
    sample = _register_sample(sample_repo)
    view = _FakeView(order_input={"sample_id": f"S-{sample.id:03d}", "customer_name": "   ", "qty": "150"})
    controller = OrderController(order_repo, sample_repo, view)

    controller._reserve_order()

    assert order_repo.list_all() == []
    assert view.errors == ["고객명을 입력해야 합니다."]
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_order_controller.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.order_controller'` 로 전부 실패.

- [ ] **Step 4: `controller/order_controller.py` 구현**

```python
from model.order import Order, OrderStatus
from model.sample_id_format import parse_sample_id

EXIT_CHOICE = "0"


class OrderController:
    def __init__(self, order_repository, sample_repository, view) -> None:
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_order_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._reserve_order()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _reserve_order(self) -> None:
        data = self._view.prompt_order_input()

        sample_id = parse_sample_id(data["sample_id"])
        if sample_id is None:
            self._view.show_error(f"유효한 시료 ID 형식이 아닙니다: {data['sample_id']}")
            return
        sample = self._sample_repository.get(sample_id)
        if sample is None:
            self._view.show_error(f"존재하지 않는 시료 ID입니다: {data['sample_id']}")
            return

        try:
            qty = int(data["qty"])
        except ValueError:
            self._view.show_error("주문 수량은 숫자로 입력해야 합니다.")
            return
        if qty <= 0:
            self._view.show_error("주문 수량은 0보다 커야 합니다.")
            return

        customer_name = data["customer_name"].strip()
        if not customer_name:
            self._view.show_error("고객명을 입력해야 합니다.")
            return

        order = self._order_repository.add(
            Order(
                id=None,
                order_no=None,
                sample_id=sample_id,
                customer_name=customer_name,
                qty=qty,
                status=OrderStatus.RESERVED,
                created_at=None,
            )
        )
        self._view.show_message(f"예약 접수 완료: {order.order_no} (상태: {order.status.value})")
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_order_controller.py -v`
Expected: 6개 테스트 모두 `PASSED`.

- [ ] **Step 6: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add view/console_view.py controller/order_controller.py test_order_controller.py
git commit -m "feat: add OrderController for sample reservation"
```

---

### Task 2: 단독 실행 진입점 `order_menu.py`

**Files:**
- Create: `order_menu.py`

**Interfaces:**
- Consumes: `controller.order_controller.OrderController`,
  `model.order_repository.SqliteOrderRepository`,
  `model.sample_repository.SqliteSampleRepository`, `view.console_view`
- Produces: 없음 (Phase 8에서 통합 `main.py`가 이 컨트롤러를 메뉴 중 하나로 흡수)

- [ ] **Step 1: `order_menu.py` 작성**

```python
from controller.order_controller import OrderController
from model.order_repository import SqliteOrderRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    OrderController(SqliteOrderRepository(), SqliteSampleRepository(), console_view).run()
```

- [ ] **Step 2: 수동 스모크 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -c "import ast; ast.parse(open('order_menu.py', encoding='utf-8').read())"`
Expected: 에러 없이 종료.

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add order_menu.py
git commit -m "feat: add standalone order_menu.py entrypoint"
```

---

### Task 3: 전체 검증 및 푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 32개(Phase 1+2) + 신규 `test_order_controller.py` 6개 = 총 38개
모두 `PASSED`.

- [ ] **Step 2: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
