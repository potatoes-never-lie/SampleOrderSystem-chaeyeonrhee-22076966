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
