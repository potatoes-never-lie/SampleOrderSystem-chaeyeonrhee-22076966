from dataclasses import dataclass


@dataclass
class Sample:
    id: int | None
    name: str
    avg_production_time: float
    yield_rate: float
    stock_qty: int = 0
