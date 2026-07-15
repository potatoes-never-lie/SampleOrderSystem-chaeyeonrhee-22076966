import random

from model.item import Item

DEFAULT_COUNT = 20

ADJECTIVES = ["Silver", "Rusty", "Quiet", "Bright", "Hollow", "Ancient", "Swift", "Gentle"]
NOUNS = ["Falcon", "Ledger", "Compass", "Beacon", "Anchor", "Lantern", "Harbor", "Cipher"]


class SeedController:
    def __init__(self, repository, view, count: int = DEFAULT_COUNT) -> None:
        self._repository = repository
        self._view = view
        self._count = count

    def run(self) -> None:
        for _ in range(self._count):
            item = Item(id=None, name=self._random_name(), description=self._random_description())
            self._repository.add(item)
        self._view.show_message(f"Seeded {self._count} dummy items.")

    @staticmethod
    def _random_name() -> str:
        return f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}"

    @staticmethod
    def _random_description() -> str:
        return f"A {random.choice(ADJECTIVES).lower()} {random.choice(NOUNS).lower()} used for testing."
