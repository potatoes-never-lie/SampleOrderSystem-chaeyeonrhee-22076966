import threading
import time

from model.order import OrderStatus


class ProductionLineWorker:
    def __init__(
        self,
        production_queue_repository,
        order_repository,
        sample_repository,
        time_scale: float = 1.0,  # ponytail: real seconds per simulated production-minute, tune for demo speed
        poll_interval: float = 0.2,
    ) -> None:
        self._queue_repository = production_queue_repository
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._time_scale = time_scale
        self._poll_interval = poll_interval
        self._lock = threading.Lock()
        self._current = None
        self._stop_event = threading.Event()
        self._thread = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._process_next():
                time.sleep(self._poll_interval)

    def _process_next(self) -> bool:
        pending = self._queue_repository.list_pending()
        if not pending:
            return False
        job = pending[0]
        self._queue_repository.dequeue(job.id)
        with self._lock:
            self._current = {"job": job, "started_at": time.monotonic()}
        time.sleep(job.total_time * self._time_scale)
        self._complete(job)
        with self._lock:
            self._current = None
        return True

    def _complete(self, job) -> None:
        order = self._order_repository.get(job.order_id)
        # Produce the full batch (actual_qty), then consume this order's qty from it —
        # net change leaves only the yield-loss surplus in stock, matching the
        # immediate stock_qty -= order.qty done at approval time for the sufficient-stock path.
        self._sample_repository.update_stock(order.sample_id, job.actual_qty - order.qty)
        self._order_repository.update_status(job.order_id, OrderStatus.CONFIRMED)

    def current_status(self) -> dict | None:
        with self._lock:
            if self._current is None:
                return None
            job = self._current["job"]
            elapsed = time.monotonic() - self._current["started_at"]
            total = job.total_time * self._time_scale
            progress = min(elapsed / total, 1.0) if total > 0 else 1.0
            return {"job": job, "progress": progress}

    def list_pending(self):
        return self._queue_repository.list_pending()
