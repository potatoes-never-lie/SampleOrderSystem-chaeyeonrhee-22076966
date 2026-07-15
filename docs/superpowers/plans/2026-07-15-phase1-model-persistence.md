# Phase 1 — 모델 & 영속성 계층 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Sample`(시료), `Order`(주문) 도메인 엔티티와 SQLite 기반 Repository를
만들어, Phase 2 이후의 모든 컨트롤러가 사용할 데이터 접근 계층을 완성한다.

**Architecture:** 기존 `model/repository.py`의 ABC + 구현체 패턴을 계승하되
엔티티별로 파일을 분리한다 (`model/sample.py` + `model/sample_repository.py`,
`model/order.py` + `model/order_repository.py`). 두 Repository는 같은 SQLite
파일(`data/sampleorder.db`)에 각자의 테이블(`samples`, `orders`)을 만든다.

**Tech Stack:** Python 3.13 표준 라이브러리 `sqlite3`, `dataclasses`, `enum`,
`datetime`. 테스트는 `pytest`, `tmp_path` fixture로 테스트마다 격리된 DB 파일 사용.

## Global Constraints

- 영속성은 SQLite 고정 (`CLAUDE.md` 결정 사항).
- 엔티티는 `@dataclass`, 타입힌트 필수 (`CLAUDE.md`).
- Repository는 ABC + 구현체 패턴 유지 (`CLAUDE.md`).
- 주문 상태 5종은 `RESERVED, REJECTED, PRODUCING, CONFIRMED, RELEASED` (`CLAUDE.md`).
- 주문번호 형식: `ORD-YYYYMMDD-NNNN` (일자별 4자리 순번, `PRD.md` 8장 예시 UI 기준).
- 재고 갱신은 항상 `update_stock(id, delta)` 하나의 원자적 연산으로 처리하고,
  결과가 음수가 되는 요청은 `ValueError`로 거부한다 (Phase 5의 백그라운드 스레드와
  동시 접근하므로 SQL의 `WHERE` 조건으로 원자성을 보장).
- 커밋은 Task 단위로 수행한다.

---

### Task 1: Sample 모델 + SQLite Repository

**Files:**
- Create: `model/sample.py`
- Create: `model/sample_repository.py`
- Test: `test_sample_repository.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `Sample(id: int | None, name: str, avg_production_time: float, yield_rate: float, stock_qty: int = 0)`
  - `SampleRepository` (ABC): `add(sample) -> Sample`, `get(sample_id) -> Sample | None`,
    `get_by_name(name) -> Sample | None`, `list_all() -> list[Sample]`,
    `search_by_name(keyword) -> list[Sample]`, `update_stock(sample_id, delta) -> Sample`
  - `SqliteSampleRepository(path: str = "data/sampleorder.db")` — 위 인터페이스의 구현체.
    Phase 2 컨트롤러가 그대로 재사용한다.

- [ ] **Step 1: `model/sample.py` 작성**

```python
from dataclasses import dataclass


@dataclass
class Sample:
    id: int | None
    name: str
    avg_production_time: float
    yield_rate: float
    stock_qty: int = 0
```

- [ ] **Step 2: `model/sample_repository.py`에 ABC 작성**

```python
from abc import ABC, abstractmethod

from model.sample import Sample


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
```

- [ ] **Step 3: 실패하는 테스트 작성 — `test_sample_repository.py`**

```python
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
```

- [ ] **Step 4: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_sample_repository.py -v`
Expected: `ModuleNotFoundError: No module named 'model.sample_repository'` 또는
`ImportError: cannot import name 'SqliteSampleRepository'` 로 전부 실패.

- [ ] **Step 5: `SqliteSampleRepository` 구현**

`model/sample_repository.py`에 이어서 추가:

```python
import os
import sqlite3

# (SampleRepository ABC는 Step 2에서 이미 작성됨, 아래를 같은 파일 하단에 추가)


class SqliteSampleRepository(SampleRepository):
    def __init__(self, path: str = "data/sampleorder.db") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(path)
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
        cursor = self._conn.execute(
            "INSERT INTO samples (name, avg_production_time, yield_rate, stock_qty) "
            "VALUES (?, ?, ?, ?)",
            (sample.name, sample.avg_production_time, sample.yield_rate, sample.stock_qty),
        )
        self._conn.commit()
        sample.id = cursor.lastrowid
        return sample

    def get(self, sample_id: int) -> Sample | None:
        row = self._conn.execute(
            "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples WHERE id = ?",
            (sample_id,),
        ).fetchone()
        return Sample(*row) if row else None

    def get_by_name(self, name: str) -> Sample | None:
        row = self._conn.execute(
            "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples WHERE name = ?",
            (name,),
        ).fetchone()
        return Sample(*row) if row else None

    def list_all(self) -> list[Sample]:
        rows = self._conn.execute(
            "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples"
        ).fetchall()
        return [Sample(*row) for row in rows]

    def search_by_name(self, keyword: str) -> list[Sample]:
        rows = self._conn.execute(
            "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples WHERE name LIKE ?",
            (f"%{keyword}%",),
        ).fetchall()
        return [Sample(*row) for row in rows]

    def update_stock(self, sample_id: int, delta: int) -> Sample:
        cursor = self._conn.execute(
            "UPDATE samples SET stock_qty = stock_qty + ? WHERE id = ? AND stock_qty + ? >= 0",
            (delta, sample_id, delta),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Cannot apply stock delta {delta} to sample {sample_id}")
        return self.get(sample_id)
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_sample_repository.py -v`
Expected: 8개 테스트 모두 `PASSED`.

- [ ] **Step 7: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add model/sample.py model/sample_repository.py test_sample_repository.py
git commit -m "feat: add Sample model and SQLite repository"
```

---

### Task 2: Order 모델(OrderStatus 포함) + SQLite Repository

**Files:**
- Create: `model/order.py`
- Create: `model/order_repository.py`
- Test: `test_order_repository.py`

**Interfaces:**
- Consumes: 없음 (Sample과 독립적인 테이블, `sample_id`는 정수 FK로만 참조하고
  Phase 1에서는 외래키 제약을 걸지 않는다 — 존재하지 않는 sample_id 검증은
  Phase 3 컨트롤러 책임)
- Produces:
  - `OrderStatus(str, Enum)`: `RESERVED, REJECTED, PRODUCING, CONFIRMED, RELEASED`
  - `Order(id: int | None, order_no: str | None, sample_id: int, customer_name: str, qty: int, status: OrderStatus, created_at: str | None)`
  - `OrderRepository` (ABC): `add(order) -> Order`, `get(order_id) -> Order | None`,
    `list_all() -> list[Order]`, `list_by_status(status) -> list[Order]`,
    `update_status(order_id, status) -> Order`
  - `SqliteOrderRepository(path: str = "data/sampleorder.db")` — `add()` 호출 시
    `order_no`(`ORD-YYYYMMDD-NNNN`)와 `created_at`(ISO 문자열)을 자동으로 채운다.
    Phase 3(주문 접수), Phase 4(승인/거절), Phase 6(모니터링), Phase 7(출고)이
    이 Repository를 그대로 사용한다.

- [ ] **Step 1: `model/order.py` 작성**

```python
from dataclasses import dataclass
from enum import Enum


class OrderStatus(str, Enum):
    RESERVED = "RESERVED"
    REJECTED = "REJECTED"
    PRODUCING = "PRODUCING"
    CONFIRMED = "CONFIRMED"
    RELEASED = "RELEASED"


@dataclass
class Order:
    id: int | None
    order_no: str | None
    sample_id: int
    customer_name: str
    qty: int
    status: OrderStatus
    created_at: str | None
```

- [ ] **Step 2: `model/order_repository.py`에 ABC 작성**

```python
from abc import ABC, abstractmethod

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
```

- [ ] **Step 3: 실패하는 테스트 작성 — `test_order_repository.py`**

```python
import pytest

from model.order import Order, OrderStatus
from model.order_repository import SqliteOrderRepository


def _repo(tmp_path):
    return SqliteOrderRepository(str(tmp_path / "test.db"))


def _new_order(sample_id=1, customer_name="SK하이닉스", qty=100):
    return Order(
        id=None, order_no=None, sample_id=sample_id, customer_name=customer_name,
        qty=qty, status=OrderStatus.RESERVED, created_at=None,
    )


def test_add_assigns_id_order_no_and_created_at(tmp_path):
    repo = _repo(tmp_path)
    order = repo.add(_new_order())
    assert order.id == 1
    assert order.order_no is not None and order.order_no.startswith("ORD-")
    assert order.created_at is not None


def test_add_increments_daily_sequence(tmp_path):
    repo = _repo(tmp_path)
    first = repo.add(_new_order(customer_name="A"))
    second = repo.add(_new_order(customer_name="B"))
    assert first.order_no.endswith("-0001")
    assert second.order_no.endswith("-0002")


def test_list_by_status_filters_correctly(tmp_path):
    repo = _repo(tmp_path)
    repo.add(_new_order(customer_name="A"))
    confirmed = repo.add(_new_order(customer_name="B"))
    repo.update_status(confirmed.id, OrderStatus.CONFIRMED)

    reserved = repo.list_by_status(OrderStatus.RESERVED)
    confirmed_list = repo.list_by_status(OrderStatus.CONFIRMED)
    assert len(reserved) == 1
    assert len(confirmed_list) == 1
    assert confirmed_list[0].id == confirmed.id


def test_update_status_changes_and_persists(tmp_path):
    repo = _repo(tmp_path)
    order = repo.add(_new_order())
    updated = repo.update_status(order.id, OrderStatus.REJECTED)
    assert updated.status == OrderStatus.REJECTED
    assert repo.get(order.id).status == OrderStatus.REJECTED


def test_update_status_raises_for_unknown_order(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(KeyError):
        repo.update_status(999, OrderStatus.REJECTED)
```

- [ ] **Step 4: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_order_repository.py -v`
Expected: `ImportError: cannot import name 'SqliteOrderRepository'` 로 전부 실패.

- [ ] **Step 5: `SqliteOrderRepository` 구현**

`model/order_repository.py`에 이어서 추가:

```python
import os
import sqlite3
from datetime import datetime

# (OrderRepository ABC는 Step 2에서 이미 작성됨, 아래를 같은 파일 하단에 추가)


class SqliteOrderRepository(OrderRepository):
    def __init__(self, path: str = "data/sampleorder.db") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(path)
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
        row = self._conn.execute(
            "SELECT id, order_no, sample_id, customer_name, qty, status, created_at "
            "FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        return self._to_order(row) if row else None

    def list_all(self) -> list[Order]:
        rows = self._conn.execute(
            "SELECT id, order_no, sample_id, customer_name, qty, status, created_at FROM orders"
        ).fetchall()
        return [self._to_order(row) for row in rows]

    def list_by_status(self, status: OrderStatus) -> list[Order]:
        rows = self._conn.execute(
            "SELECT id, order_no, sample_id, customer_name, qty, status, created_at "
            "FROM orders WHERE status = ?",
            (status.value,),
        ).fetchall()
        return [self._to_order(row) for row in rows]

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        cursor = self._conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status.value, order_id),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise KeyError(order_id)
        return self.get(order_id)

    @staticmethod
    def _to_order(row: tuple) -> Order:
        return Order(
            id=row[0], order_no=row[1], sample_id=row[2], customer_name=row[3],
            qty=row[4], status=OrderStatus(row[5]), created_at=row[6],
        )
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_order_repository.py -v`
Expected: 5개 테스트 모두 `PASSED`.

- [ ] **Step 7: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add model/order.py model/order_repository.py test_order_repository.py
git commit -m "feat: add Order model (OrderStatus) and SQLite repository"
```

---

### Task 3: 전체 검증 및 푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 `test_seed_controller.py` 3개 + 신규 `test_sample_repository.py` 8개 +
`test_order_repository.py` 5개, 총 16개 테스트 모두 `PASSED`. (`data/` 디렉터리는
`.gitignore`에 있으므로 실제 실행 시 생성되는 `data/sampleorder.db`는 커밋되지 않는다.)

- [ ] **Step 2: 커밋 로그 확인**

Run: `git -C "C:/reviewer/workspace/SampleOrderSystem" log --oneline -5`
Expected: Task 1, Task 2 커밋이 최상단에 보임.

- [ ] **Step 3: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
