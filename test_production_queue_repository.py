from model.production_job import ProductionJob
from model.production_queue_repository import SqliteProductionQueueRepository


def _repo(tmp_path):
    return SqliteProductionQueueRepository(str(tmp_path / "test.db"))


def _job(order_id, shortage_qty=10, actual_qty=11, total_time=5.5):
    return ProductionJob(
        id=None, order_id=order_id, shortage_qty=shortage_qty,
        actual_qty=actual_qty, total_time=total_time, created_at=None,
    )


def test_enqueue_assigns_id_and_created_at(tmp_path):
    repo = _repo(tmp_path)
    job = repo.enqueue(_job(order_id=1))
    assert job.id == 1
    assert job.created_at is not None


def test_list_pending_returns_jobs_in_fifo_order(tmp_path):
    repo = _repo(tmp_path)
    first = repo.enqueue(_job(order_id=1))
    second = repo.enqueue(_job(order_id=2))
    third = repo.enqueue(_job(order_id=3))

    pending = repo.list_pending()

    assert [job.order_id for job in pending] == [1, 2, 3]
    assert [job.id for job in pending] == [first.id, second.id, third.id]


def test_list_pending_preserves_job_fields(tmp_path):
    repo = _repo(tmp_path)
    repo.enqueue(_job(order_id=5, shortage_qty=20, actual_qty=22, total_time=11.0))

    pending = repo.list_pending()

    assert pending[0].shortage_qty == 20
    assert pending[0].actual_qty == 22
    assert pending[0].total_time == 11.0
