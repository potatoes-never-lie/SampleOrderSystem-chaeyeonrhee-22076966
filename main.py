import os

from controller.approval_controller import ApprovalController
from controller.main_menu_controller import MainMenuController
from controller.monitoring_controller import MonitoringController
from controller.order_controller import OrderController
from controller.production_line_controller import ProductionLineController
from controller.production_line_worker import ProductionLineWorker
from controller.release_controller import ReleaseController
from controller.sample_controller import SampleController
from model.order_repository import SqliteOrderRepository
from model.production_queue_repository import SqliteProductionQueueRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

# PRODUCTION_TIME_SCALE = real seconds per simulated production-minute.
# Default 1.0 = 60x speed-up. Set PRODUCTION_TIME_SCALE=60 for real wall-clock time.
TIME_SCALE = float(os.environ.get("PRODUCTION_TIME_SCALE", "1.0"))

if __name__ == "__main__":
    sample_repository = SqliteSampleRepository()
    order_repository = SqliteOrderRepository()
    queue_repository = SqliteProductionQueueRepository()

    worker = ProductionLineWorker(queue_repository, order_repository, sample_repository, time_scale=TIME_SCALE)
    worker.start()
    try:
        MainMenuController(
            sample_repository,
            order_repository,
            queue_repository,
            SampleController(sample_repository, console_view),
            OrderController(order_repository, sample_repository, console_view),
            ApprovalController(order_repository, sample_repository, queue_repository, console_view),
            MonitoringController(order_repository, sample_repository, console_view),
            ProductionLineController(worker, order_repository, sample_repository, console_view),
            ReleaseController(order_repository, console_view),
            console_view,
        ).run()
    finally:
        worker.stop()
