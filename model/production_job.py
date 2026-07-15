from dataclasses import dataclass


@dataclass
class ProductionJob:
    id: int | None
    order_id: int
    shortage_qty: int
    actual_qty: int
    total_time: float
    created_at: str | None
