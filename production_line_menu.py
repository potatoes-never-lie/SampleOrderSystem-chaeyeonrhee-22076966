import os

from controller.production_line_controller import ProductionLineController
from controller.production_line_worker import ProductionLineWorker
from model.order_repository import SqliteOrderRepository
from model.production_queue_repository import SqliteProductionQueueRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

# PRODUCTION_TIME_SCALE = real seconds per simulated production-minute.
# Default 1.0 = 60x speed-up (1 simulated minute -> 1 real second), good for demos.
# Set PRODUCTION_TIME_SCALE=60 to run with real wall-clock time (1 minute -> 1 minute).
TIME_SCALE = float(os.environ.get("PRODUCTION_TIME_SCALE", "1.0"))

if __name__ == "__main__":
    order_repository = SqliteOrderRepository()
    sample_repository = SqliteSampleRepository()
    queue_repository = SqliteProductionQueueRepository()

    worker = ProductionLineWorker(queue_repository, order_repository, sample_repository, time_scale=TIME_SCALE)
    worker.start()
    try:
        ProductionLineController(worker, order_repository, sample_repository, console_view).run()
    finally:
        worker.stop()
