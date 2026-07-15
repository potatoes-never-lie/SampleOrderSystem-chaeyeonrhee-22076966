import time
from dataclasses import asdict


class MonitorController:
    def __init__(self, repository, view, interval: float = 2.0) -> None:
        self._repository = repository
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
        self._view.show_message("Monitoring... (Ctrl+C to stop)")
        items = [asdict(item) for item in self._repository.list_all()]
        self._view.show_items(items)
