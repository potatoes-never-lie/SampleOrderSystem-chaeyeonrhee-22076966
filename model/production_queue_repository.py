import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

from model.production_job import ProductionJob


class ProductionQueueRepository(ABC):
    @abstractmethod
    def enqueue(self, job: ProductionJob) -> ProductionJob:
        ...

    @abstractmethod
    def list_pending(self) -> list[ProductionJob]:
        ...

    @abstractmethod
    def dequeue(self, job_id: int) -> None:
        ...


class SqliteProductionQueueRepository(ProductionQueueRepository):
    def __init__(self, path: str = "data/sampleorder.db") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS production_queue ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "order_id INTEGER NOT NULL,"
            "shortage_qty INTEGER NOT NULL,"
            "actual_qty INTEGER NOT NULL,"
            "total_time REAL NOT NULL,"
            "created_at TEXT NOT NULL)"
        )
        self._conn.commit()

    def enqueue(self, job: ProductionJob) -> ProductionJob:
        job.created_at = datetime.now().isoformat(timespec="seconds")
        cursor = self._conn.execute(
            "INSERT INTO production_queue (order_id, shortage_qty, actual_qty, total_time, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (job.order_id, job.shortage_qty, job.actual_qty, job.total_time, job.created_at),
        )
        self._conn.commit()
        job.id = cursor.lastrowid
        return job

    def list_pending(self) -> list[ProductionJob]:
        rows = self._conn.execute(
            "SELECT id, order_id, shortage_qty, actual_qty, total_time, created_at "
            "FROM production_queue ORDER BY id ASC"
        ).fetchall()
        return [ProductionJob(*row) for row in rows]

    def dequeue(self, job_id: int) -> None:
        cursor = self._conn.execute("DELETE FROM production_queue WHERE id = ?", (job_id,))
        self._conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(job_id)
