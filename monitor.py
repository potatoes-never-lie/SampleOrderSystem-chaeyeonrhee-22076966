from controller.monitor_controller import MonitorController
from model.repository import SqliteRepository, \
    CsvRepository  # swap for JsonRepository / CsvRepository / InMemoryRepository
from view import console_view

if __name__ == "__main__":
    MonitorController(CsvRepository(), console_view, interval=2.0).run()
