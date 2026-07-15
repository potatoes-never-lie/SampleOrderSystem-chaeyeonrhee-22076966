from controller.order_controller import OrderController
from model.order_repository import SqliteOrderRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    OrderController(SqliteOrderRepository(), SqliteSampleRepository(), console_view).run()
