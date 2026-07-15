from controller.seed_controller import SeedController
from model.order_repository import SqliteOrderRepository
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    SeedController(SqliteSampleRepository(), SqliteOrderRepository(), console_view).run()
