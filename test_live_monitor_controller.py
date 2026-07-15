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
