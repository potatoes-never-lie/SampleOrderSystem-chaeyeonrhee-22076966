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
