import csv
import json
import os
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict

from model.item import Item


class Repository(ABC):
    @abstractmethod
    def add(self, item: Item) -> Item:
        ...

    @abstractmethod
    def get(self, item_id: int) -> Item | None:
        ...

    @abstractmethod
    def list_all(self) -> list[Item]:
        ...

    @abstractmethod
    def update(self, item: Item) -> None:
        ...

    @abstractmethod
    def delete(self, item_id: int) -> None:
        ...


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._items: dict[int, Item] = {}
        self._next_id = 1

    def add(self, item: Item) -> Item:
        item.id = self._next_id
        self._items[item.id] = item
        self._next_id += 1
        return item

    def get(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    def list_all(self) -> list[Item]:
        return list(self._items.values())

    def update(self, item: Item) -> None:
        if item.id not in self._items:
            raise KeyError(item.id)
        self._items[item.id] = item

    def delete(self, item_id: int) -> None:
        if item_id not in self._items:
            raise KeyError(item_id)
        del self._items[item_id]


class _FileRepository(Repository):
    """Shared load-into-memory / rewrite-whole-file behavior for CSV and JSON backends."""

    def __init__(self, path: str) -> None:
        self._path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._items: dict[int, Item] = self._load()
        self._next_id = max(self._items, default=0) + 1

    def add(self, item: Item) -> Item:
        item.id = self._next_id
        self._items[item.id] = item
        self._next_id += 1
        self._save()
        return item

    def get(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    def list_all(self) -> list[Item]:
        return list(self._items.values())

    def update(self, item: Item) -> None:
        if item.id not in self._items:
            raise KeyError(item.id)
        self._items[item.id] = item
        self._save()

    def delete(self, item_id: int) -> None:
        if item_id not in self._items:
            raise KeyError(item_id)
        del self._items[item_id]
        self._save()

    def _load(self) -> dict[int, Item]:
        raise NotImplementedError

    def _save(self) -> None:
        raise NotImplementedError


class CsvRepository(_FileRepository):
    FIELDNAMES = ["id", "name", "description"]

    def __init__(self, path: str = "data/items.csv") -> None:
        super().__init__(path)

    def _load(self) -> dict[int, Item]:
        if not os.path.exists(self._path):
            return {}
        with open(self._path, newline="", encoding="utf-8") as f:
            return {
                int(row["id"]): Item(id=int(row["id"]), name=row["name"], description=row["description"])
                for row in csv.DictReader(f)
            }

    def _save(self) -> None:
        with open(self._path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            for item in self._items.values():
                writer.writerow({"id": item.id, "name": item.name, "description": item.description})


class JsonRepository(_FileRepository):
    def __init__(self, path: str = "data/items.json") -> None:
        super().__init__(path)

    def _load(self) -> dict[int, Item]:
        if not os.path.exists(self._path):
            return {}
        with open(self._path, encoding="utf-8") as f:
            return {row["id"]: Item(**row) for row in json.load(f)}

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump([asdict(item) for item in self._items.values()], f, ensure_ascii=False, indent=2)


class SqliteRepository(Repository):
    """No in-memory cache: every call queries data/items.db directly via sqlite3."""

    def __init__(self, path: str = "data/items.db") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS items ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "name TEXT NOT NULL,"
            "description TEXT NOT NULL)"
        )
        self._conn.commit()

    def add(self, item: Item) -> Item:
        cursor = self._conn.execute(
            "INSERT INTO items (name, description) VALUES (?, ?)", (item.name, item.description)
        )
        self._conn.commit()
        item.id = cursor.lastrowid
        return item

    def get(self, item_id: int) -> Item | None:
        row = self._conn.execute("SELECT id, name, description FROM items WHERE id = ?", (item_id,)).fetchone()
        return Item(*row) if row else None

    def list_all(self) -> list[Item]:
        rows = self._conn.execute("SELECT id, name, description FROM items").fetchall()
        return [Item(*row) for row in rows]

    def update(self, item: Item) -> None:
        cursor = self._conn.execute(
            "UPDATE items SET name = ?, description = ? WHERE id = ?",
            (item.name, item.description, item.id),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(item.id)

    def delete(self, item_id: int) -> None:
        cursor = self._conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self._conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(item_id)
