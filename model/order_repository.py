import os
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime

from model.order import Order, OrderStatus


class OrderRepository(ABC):
    @abstractmethod
    def add(self, order: Order) -> Order:
        ...

    @abstractmethod
    def get(self, order_id: int) -> Order | None:
        ...

    @abstractmethod
    def list_all(self) -> list[Order]:
        ...

    @abstractmethod
    def list_by_status(self, status: OrderStatus) -> list[Order]:
        ...

    @abstractmethod
    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        ...


class SqliteOrderRepository(OrderRepository):
    def __init__(self, path: str = "data/sampleorder.db") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # check_same_thread=False + a per-instance lock: the production line
        # background thread (Phase 5) and the console's main thread both call
        # into this same repository instance.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS orders ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "order_no TEXT NOT NULL UNIQUE,"
            "sample_id INTEGER NOT NULL,"
            "customer_name TEXT NOT NULL,"
            "qty INTEGER NOT NULL,"
            "status TEXT NOT NULL,"
            "created_at TEXT NOT NULL)"
        )
        self._conn.commit()

    def add(self, order: Order) -> Order:
        created_at = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            order.order_no = self._next_order_no(created_at)
            order.created_at = created_at
            cursor = self._conn.execute(
                "INSERT INTO orders (order_no, sample_id, customer_name, qty, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (order.order_no, order.sample_id, order.customer_name, order.qty,
                 order.status.value, order.created_at),
            )
            self._conn.commit()
            order.id = cursor.lastrowid
            return order

    def _next_order_no(self, created_at: str) -> str:
        date_part = created_at[:10].replace("-", "")
        count = self._conn.execute(
            "SELECT COUNT(*) FROM orders WHERE order_no LIKE ?",
            (f"ORD-{date_part}-%",),
        ).fetchone()[0]
        return f"ORD-{date_part}-{count + 1:04d}"

    def get(self, order_id: int) -> Order | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, order_no, sample_id, customer_name, qty, status, created_at "
                "FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
            return self._to_order(row) if row else None

    def list_all(self) -> list[Order]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, order_no, sample_id, customer_name, qty, status, created_at FROM orders"
            ).fetchall()
            return [self._to_order(row) for row in rows]

    def list_by_status(self, status: OrderStatus) -> list[Order]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, order_no, sample_id, customer_name, qty, status, created_at "
                "FROM orders WHERE status = ?",
                (status.value,),
            ).fetchall()
            return [self._to_order(row) for row in rows]

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status.value, order_id),
            )
            self._conn.commit()
            if cursor.rowcount == 0:
                raise KeyError(order_id)
            row = self._conn.execute(
                "SELECT id, order_no, sample_id, customer_name, qty, status, created_at "
                "FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
            return self._to_order(row)

    @staticmethod
    def _to_order(row: tuple) -> Order:
        return Order(
            id=row[0], order_no=row[1], sample_id=row[2], customer_name=row[3],
            qty=row[4], status=OrderStatus(row[5]), created_at=row[6],
        )
