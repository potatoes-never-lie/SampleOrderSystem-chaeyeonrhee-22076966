from controller.approval_controller import ApprovalController
from model.order_repository import SqliteOrderRepository
from model.production_queue_repository import SqliteProductionQueueRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    ApprovalController(
        SqliteOrderRepository(), SqliteSampleRepository(), SqliteProductionQueueRepository(), console_view
    ).run()
