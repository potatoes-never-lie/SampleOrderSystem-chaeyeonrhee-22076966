import random

from model.order import Order, OrderStatus
from model.sample import Sample

DEFAULT_SAMPLE_COUNT = 10
DEFAULT_ORDER_COUNT = 20

MATERIALS = ["실리콘", "GaN", "SiC", "포토레지스트", "산화막"]
SAMPLE_TYPES = ["웨이퍼-8인치", "웨이퍼-6인치", "에피택셜-4인치", "파워기판-6인치", "PR7", "SiO2"]
CUSTOMERS = ["SK하이닉스", "삼성전자 파운드리", "LG이노텍", "DB하이텍", "한양대 연구실", "팹리스 A"]


class SeedController:
    def __init__(
        self,
        sample_repository,
        order_repository,
        view,
        sample_count: int = DEFAULT_SAMPLE_COUNT,
        order_count: int = DEFAULT_ORDER_COUNT,
    ) -> None:
        self._sample_repository = sample_repository
        self._order_repository = order_repository
        self._view = view
        self._sample_count = sample_count
        self._order_count = order_count

    def run(self) -> None:
        samples = [self._add_random_sample(i) for i in range(self._sample_count)]
        if samples:
            for _ in range(self._order_count):
                self._add_random_order(samples)
        self._view.show_message(f"Seeded {self._sample_count} samples and {self._order_count} orders.")

    def _add_random_sample(self, index: int) -> Sample:
        name = f"{random.choice(MATERIALS)} {random.choice(SAMPLE_TYPES)} #{index + 1}"
        return self._sample_repository.add(
            Sample(
                id=None,
                name=name,
                avg_production_time=round(random.uniform(0.1, 1.0), 2),
                yield_rate=round(random.uniform(0.7, 0.99), 2),
                stock_qty=random.randint(0, 500),
            )
        )

    def _add_random_order(self, samples: list) -> None:
        sample = random.choice(samples)
        self._order_repository.add(
            Order(
                id=None,
                order_no=None,
                sample_id=sample.id,
                customer_name=random.choice(CUSTOMERS),
                qty=random.randint(1, 300),
                status=OrderStatus.RESERVED,
                created_at=None,
            )
        )
