import pytest

from model.sample import Sample
from model.sample_repository import SqliteSampleRepository


def _repo(tmp_path):
    return SqliteSampleRepository(str(tmp_path / "test.db"))


def test_add_assigns_id(tmp_path):
    repo = _repo(tmp_path)
    sample = repo.add(
        Sample(id=None, name="실리콘 웨이퍼-8인치", avg_production_time=0.5, yield_rate=0.92, stock_qty=100)
    )
    assert sample.id == 1


def test_get_by_name_finds_registered_sample(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="GaN 에피택셜-4인치", avg_production_time=0.3, yield_rate=0.78, stock_qty=0))
    found = repo.get_by_name("GaN 에피택셜-4인치")
    assert found is not None
    assert found.yield_rate == 0.78


def test_get_by_name_returns_none_when_missing(tmp_path):
    repo = _repo(tmp_path)
    assert repo.get_by_name("없음") is None


def test_list_all_returns_every_registered_sample(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    repo.add(Sample(id=None, name="B", avg_production_time=0.2, yield_rate=0.8, stock_qty=0))
    assert {s.name for s in repo.list_all()} == {"A", "B"}


def test_search_by_name_matches_partial_keyword(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="실리콘 웨이퍼-8인치", avg_production_time=0.5, yield_rate=0.92, stock_qty=0))
    repo.add(Sample(id=None, name="산화막 웨이퍼-SiO2", avg_production_time=0.6, yield_rate=0.88, stock_qty=0))
    repo.add(Sample(id=None, name="포토레지스트-PR7", avg_production_time=0.2, yield_rate=0.95, stock_qty=0))
    results = repo.search_by_name("웨이퍼")
    assert {s.name for s in results} == {"실리콘 웨이퍼-8인치", "산화막 웨이퍼-SiO2"}


def test_update_stock_increments_quantity(tmp_path):
    repo = _repo(tmp_path)
    sample = repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=10))
    updated = repo.update_stock(sample.id, 5)
    assert updated.stock_qty == 15


def test_update_stock_decrements_quantity(tmp_path):
    repo = _repo(tmp_path)
    sample = repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=10))
    updated = repo.update_stock(sample.id, -4)
    assert updated.stock_qty == 6


def test_update_stock_rejects_negative_result(tmp_path):
    repo = _repo(tmp_path)
    sample = repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=3))
    with pytest.raises(ValueError):
        repo.update_stock(sample.id, -4)


def test_search_by_name_matches_sample_id_dash_format(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="실리콘 웨이퍼-8인치", avg_production_time=0.5, yield_rate=0.92, stock_qty=0))
    target = repo.add(Sample(id=None, name="포토레지스트-PR7", avg_production_time=0.2, yield_rate=0.95, stock_qty=0))

    results = repo.search_by_name(f"S-{target.id:03d}")

    assert [s.id for s in results] == [target.id]


def test_search_by_name_matches_plain_numeric_id(tmp_path):
    repo = _repo(tmp_path)
    target = repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))

    results = repo.search_by_name(str(target.id))

    assert [s.id for s in results] == [target.id]


def test_search_by_name_does_not_duplicate_when_name_and_id_both_match(tmp_path):
    repo = _repo(tmp_path)
    sample = repo.add(Sample(id=None, name="1", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))

    results = repo.search_by_name("1")

    assert len(results) == 1
    assert results[0].id == sample.id


def test_search_by_name_still_matches_partial_name_when_not_an_id(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="산화막 웨이퍼-SiO2", avg_production_time=0.6, yield_rate=0.88, stock_qty=0))

    results = repo.search_by_name("웨이퍼")

    assert len(results) == 1
