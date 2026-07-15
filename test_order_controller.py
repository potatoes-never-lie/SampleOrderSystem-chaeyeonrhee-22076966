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
