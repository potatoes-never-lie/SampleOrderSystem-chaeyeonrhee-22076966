from controller.sample_controller import SampleController
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    SampleController(SqliteSampleRepository(), console_view).run()
