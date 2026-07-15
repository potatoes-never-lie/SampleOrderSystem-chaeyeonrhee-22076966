from controller.seed_controller import SeedController
from model.repository import InMemoryRepository


class _RecordingView:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def show_message(self, msg: str) -> None:
        self.messages.append(msg)


def test_run_adds_requested_number_of_items():
    repo = InMemoryRepository()
    view = _RecordingView()

    SeedController(repo, view, count=5).run()

    items = repo.list_all()
    assert len(items) == 5
    for item in items:
        assert item.name.strip() != ""
        assert item.description.strip() != ""


def test_run_reports_seeded_count():
    repo = InMemoryRepository()
    view = _RecordingView()

    SeedController(repo, view, count=3).run()

    assert view.messages == ["Seeded 3 dummy items."]


def test_run_with_zero_count_adds_nothing():
    repo = InMemoryRepository()
    view = _RecordingView()

    SeedController(repo, view, count=0).run()

    assert repo.list_all() == []
    assert view.messages == ["Seeded 0 dummy items."]
