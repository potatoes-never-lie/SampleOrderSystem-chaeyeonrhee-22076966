from dataclasses import dataclass


@dataclass
class Item:
    id: int | None
    name: str
    description: str
