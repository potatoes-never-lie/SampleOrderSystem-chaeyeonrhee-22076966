from controller.item_controller import ItemController
from model.repository import CsvRepository  # swap for JsonRepository / SqliteRepository / InMemoryRepository
from view import console_view

if __name__ == "__main__":
    ItemController(CsvRepository(), console_view).run()
