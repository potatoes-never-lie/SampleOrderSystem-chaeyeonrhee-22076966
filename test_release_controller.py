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
