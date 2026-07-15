import time

from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.order import Order, OrderStatus
from model.order_repository import SqliteOrderRepository
from model.production_job import ProductionJob
from model.production_queue_repository import SqliteProductionQueueRepository
from controller.production_line_worker import ProductionLineWorker


def _repos(tmp_path):
    path = str(tmp_path / "test.db")
    return SqliteSampleRepository(path), SqliteOrderRepository(path), SqliteProductionQueueRepository(path)


def _producing_order(order_repo, sample_id, qty=50):
    order = order_repo.add(
        Order(id=None, order_no=None, sample_id=sample_id, customer_name="SK하이닉스",
              qty=qty, status=OrderStatus.RESERVED, created_at=None)
    )
    return order_repo.update_status(order.id, OrderStatus.PRODUCING)


def test_process_next_returns_false_when_queue_empty(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.0)

    assert worker._process_next() is False


def test_process_next_completes_job_and_updates_order_and_stock(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.5, yield_rate=0.8, stock_qty=30))
    order = _producing_order(order_repo, sample.id, qty=80)
    queue_repo.enqueue(
        ProductionJob(id=None, order_id=order.id, shortage_qty=50, actual_qty=63, total_time=0.01, created_at=None)
    )
    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.01)

    processed = worker._process_next()

    assert processed is True
    updated_order = order_repo.get(order.id)
    updated_sample = sample_repo.get(sample.id)
    assert updated_order.status == OrderStatus.CONFIRMED
    assert updated_sample.stock_qty == 30 + 63 - 80
    assert queue_repo.list_pending() == []
    assert worker.current_status() is None


def test_process_next_processes_jobs_in_fifo_order(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    first_order = _producing_order(order_repo, sample.id, qty=10)
    second_order = _producing_order(order_repo, sample.id, qty=10)
    queue_repo.enqueue(ProductionJob(id=None, order_id=first_order.id, shortage_qty=10, actual_qty=12, total_time=0.01, created_at=None))
    queue_repo.enqueue(ProductionJob(id=None, order_id=second_order.id, shortage_qty=10, actual_qty=12, total_time=0.01, created_at=None))
    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.01)

    worker._process_next()

    assert order_repo.get(first_order.id).status == OrderStatus.CONFIRMED
    assert order_repo.get(second_order.id).status == OrderStatus.PRODUCING
    assert [j.order_id for j in worker.list_pending()] == [second_order.id]


def test_start_and_stop_processes_queued_job_in_background(tmp_path):
    sample_repo, order_repo, queue_repo = _repos(tmp_path)
    sample = sample_repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    order = _producing_order(order_repo, sample.id, qty=10)
    queue_repo.enqueue(
        ProductionJob(id=None, order_id=order.id, shortage_qty=10, actual_qty=12, total_time=1.0, created_at=None)
    )
    worker = ProductionLineWorker(queue_repo, order_repo, sample_repo, time_scale=0.05, poll_interval=0.02)

    worker.start()
    time.sleep(0.03)
    status = worker.current_status()
    assert status is not None
    assert status["job"].order_id == order.id
    assert 0.0 <= status["progress"] <= 1.0

    deadline = time.monotonic() + 2.0
    while order_repo.get(order.id).status != OrderStatus.CONFIRMED and time.monotonic() < deadline:
        time.sleep(0.02)
    worker.stop()

    assert order_repo.get(order.id).status == OrderStatus.CONFIRMED
    assert sample_repo.get(sample.id).stock_qty == 12 - 10
