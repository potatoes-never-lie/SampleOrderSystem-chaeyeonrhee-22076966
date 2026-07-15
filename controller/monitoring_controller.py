from model.order import OrderStatus

EXIT_CHOICE = "0"
ORDER_COUNT_STATUSES = [OrderStatus.RESERVED, OrderStatus.CONFIRMED, OrderStatus.PRODUCING, OrderStatus.RELEASED]
DEMAND_STATUSES = [OrderStatus.RESERVED, OrderStatus.PRODUCING]


class MonitoringController:
    def __init__(self, order_repository, sample_repository, view) -> None:
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_monitor_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._show_order_counts()
            elif choice == "2":
                self._show_inventory_status()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _show_order_counts(self) -> None:
        counts = [
            (status, len(self._order_repository.list_by_status(status)))
            for status in ORDER_COUNT_STATUSES
        ]
        self._view.show_order_counts(counts)

    def _show_inventory_status(self) -> None:
        demand_by_sample = self._demand_by_sample()
        entries = []
        for sample in self._sample_repository.list_all():
            demand = demand_by_sample.get(sample.id, 0)
            entries.append((sample, demand, self._inventory_state(sample.stock_qty, demand)))
        self._view.show_inventory_status(entries)

    def _demand_by_sample(self) -> dict[int, int]:
        demand: dict[int, int] = {}
        for status in DEMAND_STATUSES:
            for order in self._order_repository.list_by_status(status):
                demand[order.sample_id] = demand.get(order.sample_id, 0) + order.qty
        return demand

    @staticmethod
    def _inventory_state(stock_qty: int, demand: int) -> str:
        if stock_qty == 0:
            return "고갈"
        if stock_qty >= demand:
            return "여유"
        return "부족"
