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
