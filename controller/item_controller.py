from dataclasses import asdict

from model.item import Item

EXIT_CHOICE = "5"


class ItemController:
    def __init__(self, repository, view) -> None:
        self._repository = repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._list_items()
            elif choice == "2":
                self._add_item()
            elif choice == "3":
                self._update_item()
            elif choice == "4":
                self._delete_item()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _list_items(self) -> None:
        items = [asdict(item) for item in self._repository.list_all()]
        self._view.show_items(items)

    def _add_item(self) -> None:
        data = self._view.prompt_item_input()
        item = Item(id=None, name=data["name"], description=data["description"])
        self._repository.add(item)
        self._view.show_message(f"Added item {item.id}")

    def _update_item(self) -> None:
        item_id = self._read_id()
        if item_id is None:
            return
        data = self._view.prompt_item_input()
        try:
            self._repository.update(Item(id=item_id, name=data["name"], description=data["description"]))
            self._view.show_message(f"Updated item {item_id}")
        except KeyError:
            self._view.show_error(f"Item {item_id} not found")

    def _delete_item(self) -> None:
        item_id = self._read_id()
        if item_id is None:
            return
        try:
            self._repository.delete(item_id)
            self._view.show_message(f"Deleted item {item_id}")
        except KeyError:
            self._view.show_error(f"Item {item_id} not found")

    def _read_id(self) -> int | None:
        raw = self._view.prompt_id()
        try:
            return int(raw)
        except ValueError:
            self._view.show_error(f"'{raw}' is not a valid id")
            return None
