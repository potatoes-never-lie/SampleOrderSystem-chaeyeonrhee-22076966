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
