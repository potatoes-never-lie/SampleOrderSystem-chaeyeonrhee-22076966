from controller.seed_controller import SeedController
from model.repository import CsvRepository  # swap for JsonRepository / SqliteRepository / InMemoryRepository
from view import console_view

if __name__ == "__main__":
    SeedController(CsvRepository(), console_view).run()
