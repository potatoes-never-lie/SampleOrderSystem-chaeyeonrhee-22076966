from model.sample_repository import SqliteSampleRepository
from model.order_repository import SqliteOrderRepository
from controller.seed_controller import SeedController


class _RecordingView:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def show_message(self, msg: str) -> None:
        self.messages.append(msg)


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path)


def test_run_adds_requested_number_of_samples_and_orders(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    view = _RecordingView()

    SeedController(sample_repo, order_repo, view, sample_count=5, order_count=8).run()

    assert len(sample_repo.list_all()) == 5
    assert len(order_repo.list_all()) == 8


def test_run_reports_seeded_counts(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    view = _RecordingView()

    SeedController(sample_repo, order_repo, view, sample_count=3, order_count=4).run()

    assert view.messages == ["Seeded 3 samples and 4 orders."]


def test_run_with_zero_counts_adds_nothing(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    view = _RecordingView()

    SeedController(sample_repo, order_repo, view, sample_count=0, order_count=0).run()

    assert sample_repo.list_all() == []
    assert order_repo.list_all() == []
    assert view.messages == ["Seeded 0 samples and 0 orders."]


def test_generated_orders_reference_existing_samples(tmp_path):
    sample_repo, order_repo = _repos(tmp_path)
    view = _RecordingView()

    SeedController(sample_repo, order_repo, view, sample_count=4, order_count=10).run()

    sample_ids = {s.id for s in sample_repo.list_all()}
    assert all(order.sample_id in sample_ids for order in order_repo.list_all())
