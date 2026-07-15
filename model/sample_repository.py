import os
import sqlite3
import threading
from abc import ABC, abstractmethod

from model.sample import Sample
from model.sample_id_format import parse_sample_id


class SampleRepository(ABC):
    @abstractmethod
    def add(self, sample: Sample) -> Sample:
        ...

    @abstractmethod
    def get(self, sample_id: int) -> Sample | None:
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> Sample | None:
        ...

    @abstractmethod
    def list_all(self) -> list[Sample]:
        ...

    @abstractmethod
    def search_by_name(self, keyword: str) -> list[Sample]:
        ...

    @abstractmethod
    def update_stock(self, sample_id: int, delta: int) -> Sample:
        ...


class SqliteSampleRepository(SampleRepository):
    def __init__(self, path: str = "data/sampleorder.db") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # check_same_thread=False + a per-instance lock: the production line
        # background thread (Phase 5) and the console's main thread both call
        # into this same repository instance.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS samples ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "name TEXT NOT NULL UNIQUE,"
            "avg_production_time REAL NOT NULL,"
            "yield_rate REAL NOT NULL,"
            "stock_qty INTEGER NOT NULL DEFAULT 0)"
        )
        self._conn.commit()

    def add(self, sample: Sample) -> Sample:
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO samples (name, avg_production_time, yield_rate, stock_qty) "
                "VALUES (?, ?, ?, ?)",
                (sample.name, sample.avg_production_time, sample.yield_rate, sample.stock_qty),
            )
            self._conn.commit()
            sample.id = cursor.lastrowid
            return sample

    def get(self, sample_id: int) -> Sample | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples WHERE id = ?",
                (sample_id,),
            ).fetchone()
            return Sample(*row) if row else None

    def get_by_name(self, name: str) -> Sample | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples WHERE name = ?",
                (name,),
            ).fetchone()
            return Sample(*row) if row else None

    def list_all(self) -> list[Sample]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples"
            ).fetchall()
            return [Sample(*row) for row in rows]

    def search_by_name(self, keyword: str) -> list[Sample]:
        sample_id = parse_sample_id(keyword)
        with self._lock:
            if sample_id is not None:
                rows = self._conn.execute(
                    "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples "
                    "WHERE name LIKE ? OR id = ?",
                    (f"%{keyword}%", sample_id),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples WHERE name LIKE ?",
                    (f"%{keyword}%",),
                ).fetchall()
            return [Sample(*row) for row in rows]

    def update_stock(self, sample_id: int, delta: int) -> Sample:
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE samples SET stock_qty = stock_qty + ? WHERE id = ? AND stock_qty + ? >= 0",
                (delta, sample_id, delta),
            )
            self._conn.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"Cannot apply stock delta {delta} to sample {sample_id}")
            row = self._conn.execute(
                "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples WHERE id = ?",
                (sample_id,),
            ).fetchone()
            return Sample(*row)
