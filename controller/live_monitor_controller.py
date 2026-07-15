import time


class LiveMonitorController:
    def __init__(self, sample_repository, order_repository, view, interval: float = 2.0) -> None:
        self._sample_repository = sample_repository
        self._order_repository = order_repository
        self._view = view
        self._interval = interval

    def run(self) -> None:
        try:
            while True:
                self._tick()
                time.sleep(self._interval)
        except KeyboardInterrupt:
            self._view.show_message("Monitoring stopped.")

    def _tick(self) -> None:
        self._view.clear_screen()
        self._view.show_message("Live data monitor... (Ctrl+C to stop)")
        self._view.show_samples(self._sample_repository.list_all())
        self._view.show_order_list(self._order_repository.list_all())
