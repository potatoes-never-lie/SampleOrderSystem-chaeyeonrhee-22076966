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
