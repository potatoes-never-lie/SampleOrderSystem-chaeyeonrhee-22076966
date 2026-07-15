from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.order import Order, OrderStatus
from model.order_repository import SqliteOrderRepository
from controller.monitoring_controller import MonitoringController


class _FakeView:
    def __init__(self):
        self.order_counts = None
        self.inventory_entries = None

    def show_order_counts(self, counts):
        self.order_counts = counts

    def show_inventory_status(self, entries):
        self.inventory_entries = entries


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path)


def _order(order_repo, sample_id, qty, status):
    order = order_repo.add(
        Order(id=None, order_no=None, sample_id=sample_id, customer_name="A",
              qty=qty, status=OrderStatus.RESERVED, created_at=None)
    )
    if status != OrderStatus.RESERVED:
        order = order_repo.update_status(order.id, status)
    return order


def test_show_order_counts_excludes_rejected(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=100))
    _order(order_repo, sample.id, 10, OrderStatus.RESERVED)
    _order(order_repo, sample.id, 10, OrderStatus.CONFIRMED)
    _order(order_repo, sample.id, 10, OrderStatus.CONFIRMED)
    _order(order_repo, sample.id, 10, OrderStatus.PRODUCING)
    _order(order_repo, sample.id, 10, OrderStatus.RELEASED)
    _order(order_repo, sample.id, 10, OrderStatus.REJECTED)
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_order_counts()

    counts = dict(view.order_counts)
    assert counts[OrderStatus.RESERVED] == 1
    assert counts[OrderStatus.CONFIRMED] == 2
    assert counts[OrderStatus.PRODUCING] == 1
    assert counts[OrderStatus.RELEASED] == 1
    assert OrderStatus.REJECTED not in counts


def test_show_inventory_status_reports_surplus_when_stock_covers_demand(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=100))
    _order(order_repo, sample.id, 30, OrderStatus.RESERVED)
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_inventory_status()

    entry = next(e for e in view.inventory_entries if e[0].id == sample.id)
    assert entry[1] == 30
    assert entry[2] == "여유"


def test_show_inventory_status_reports_shortage_when_demand_exceeds_stock(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=10))
    _order(order_repo, sample.id, 5, OrderStatus.RESERVED)
    _order(order_repo, sample.id, 10, OrderStatus.PRODUCING)
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_inventory_status()

    entry = next(e for e in view.inventory_entries if e[0].id == sample.id)
    assert entry[1] == 15
    assert entry[2] == "부족"


def test_show_inventory_status_reports_depleted_when_stock_zero_even_without_demand(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_inventory_status()

    entry = next(e for e in view.inventory_entries if e[0].id == sample.id)
    assert entry[1] == 0
    assert entry[2] == "고갈"


def test_show_inventory_status_ignores_confirmed_and_released_demand(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=5))
    _order(order_repo, sample.id, 1000, OrderStatus.CONFIRMED)
    _order(order_repo, sample.id, 1000, OrderStatus.RELEASED)
    view = _FakeView()
    controller = MonitoringController(order_repo, sample_repo, view)

    controller._show_inventory_status()

    entry = next(e for e in view.inventory_entries if e[0].id == sample.id)
    assert entry[1] == 0
    assert entry[2] == "여유"
