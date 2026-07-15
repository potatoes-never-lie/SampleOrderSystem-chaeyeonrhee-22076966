EXIT_CHOICE = "0"


class MainMenuController:
    def __init__(
        self,
        sample_repository,
        order_repository,
        production_queue_repository,
        sample_controller,
        order_controller,
        approval_controller,
        monitoring_controller,
        production_line_controller,
        release_controller,
        view,
    ) -> None:
        self._sample_repository = sample_repository
        self._order_repository = order_repository
        self._production_queue_repository = production_queue_repository
        self._sample_controller = sample_controller
        self._order_controller = order_controller
        self._approval_controller = approval_controller
        self._monitoring_controller = monitoring_controller
        self._production_line_controller = production_line_controller
        self._release_controller = release_controller
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_main_menu(self._build_summary())
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._sample_controller.run()
            elif choice == "2":
                self._order_controller.run()
            elif choice == "3":
                self._approval_controller.run()
            elif choice == "4":
                self._monitoring_controller.run()
            elif choice == "5":
                self._production_line_controller.run()
            elif choice == "6":
                self._release_controller.run()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _build_summary(self) -> dict:
        samples = self._sample_repository.list_all()
        return {
            "sample_count": len(samples),
            "total_stock": sum(sample.stock_qty for sample in samples),
            "order_count": len(self._order_repository.list_all()),
            "pending_production": len(self._production_queue_repository.list_pending()),
        }
