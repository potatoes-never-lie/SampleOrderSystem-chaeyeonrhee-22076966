EXIT_CHOICE = "0"


class ProductionLineController:
    def __init__(self, worker, order_repository, sample_repository, view) -> None:
        self._worker = worker
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_production_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._show_status()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _show_status(self) -> None:
        self._view.show_section("생산 현황")
        status = self._worker.current_status()
        if status is None:
            self._view.show_message("현재 생산 중인 작업이 없습니다.")
        else:
            job = status["job"]
            order = self._order_repository.get(job.order_id)
            sample = self._sample_repository.get(order.sample_id)
            self._view.show_production_status(job, order, sample, status["progress"])

        self._view.show_section("대기 주문")
        entries = [(job, self._order_repository.get(job.order_id)) for job in self._worker.list_pending()]
        self._view.show_pending_queue(entries)
