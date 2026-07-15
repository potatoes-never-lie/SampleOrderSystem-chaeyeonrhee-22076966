from controller.live_monitor_controller import LiveMonitorController
from model.order_repository import SqliteOrderRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    LiveMonitorController(SqliteSampleRepository(), SqliteOrderRepository(), console_view, interval=2.0).run()
