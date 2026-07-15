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
