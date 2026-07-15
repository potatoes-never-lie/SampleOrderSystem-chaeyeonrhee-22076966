from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.sample_id_format import format_sample_id
from controller.sample_controller import SampleController


class _FakeView:
    def __init__(self, sample_input=None, search_keyword=None):
        self.messages = []
        self.errors = []
        self.shown_samples = None
        self._sample_input = sample_input
        self._search_keyword = search_keyword

    def prompt_sample_input(self):
        return self._sample_input

    def prompt_search_keyword(self):
        return self._search_keyword

    def show_samples(self, samples):
        self.shown_samples = samples

    def show_message(self, msg):
        self.messages.append(msg)

    def show_error(self, msg):
        self.errors.append(msg)


def _repo(tmp_path):
    return SqliteSampleRepository(str(tmp_path / "test.db"))


def test_register_sample_adds_to_repository(tmp_path):
    repo = _repo(tmp_path)
    view = _FakeView(sample_input={"name": "실리콘 웨이퍼-8인치", "avg_production_time": "0.5", "yield_rate": "0.92"})
    controller = SampleController(repo, view)

    controller._register_sample()

    samples = repo.list_all()
    assert len(samples) == 1
    assert samples[0].name == "실리콘 웨이퍼-8인치"
    assert samples[0].stock_qty == 0
    assert view.messages == [f"시료 등록 완료: [{format_sample_id(samples[0].id)}] 실리콘 웨이퍼-8인치"]


def test_register_sample_rejects_duplicate_name(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    view = _FakeView(sample_input={"name": "A", "avg_production_time": "0.2", "yield_rate": "0.8"})
    controller = SampleController(repo, view)

    controller._register_sample()

    assert len(repo.list_all()) == 1
    assert view.errors == ["이미 등록된 시료 이름입니다: A"]


def test_register_sample_rejects_non_numeric_input(tmp_path):
    repo = _repo(tmp_path)
    view = _FakeView(sample_input={"name": "A", "avg_production_time": "빠름", "yield_rate": "0.9"})
    controller = SampleController(repo, view)

    controller._register_sample()

    assert repo.list_all() == []
    assert view.errors == ["평균 생산시간과 수율은 숫자로 입력해야 합니다."]


def test_register_sample_rejects_yield_rate_out_of_range(tmp_path):
    repo = _repo(tmp_path)
    view = _FakeView(sample_input={"name": "A", "avg_production_time": "0.5", "yield_rate": "1.5"})
    controller = SampleController(repo, view)

    controller._register_sample()

    assert repo.list_all() == []
    assert view.errors == ["수율은 0보다 크고 1 이하여야 합니다."]


def test_list_samples_shows_all_registered(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=5))
    repo.add(Sample(id=None, name="B", avg_production_time=0.2, yield_rate=0.8, stock_qty=10))
    view = _FakeView()
    controller = SampleController(repo, view)

    controller._list_samples()

    assert {s.name for s in view.shown_samples} == {"A", "B"}


def test_search_samples_delegates_to_repository_search(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="실리콘 웨이퍼-8인치", avg_production_time=0.5, yield_rate=0.92, stock_qty=0))
    target = repo.add(Sample(id=None, name="포토레지스트-PR7", avg_production_time=0.2, yield_rate=0.95, stock_qty=0))
    view = _FakeView(search_keyword=format_sample_id(target.id))
    controller = SampleController(repo, view)

    controller._search_samples()

    assert [s.id for s in view.shown_samples] == [target.id]
