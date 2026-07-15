from controller.release_controller import ReleaseController
from model.order_repository import SqliteOrderRepository
from view import console_view

if __name__ == "__main__":
    ReleaseController(SqliteOrderRepository(), console_view).run()
