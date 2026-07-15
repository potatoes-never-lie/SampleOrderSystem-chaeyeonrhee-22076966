MENU_TEXT = """
1. List items
2. Add item
3. Update item
4. Delete item
5. Exit
"""


def prompt_menu() -> str:
    print(MENU_TEXT)
    return input("Select an option: ")


def prompt_item_input() -> dict:
    name = input("Name: ")
    description = input("Description: ")
    return {"name": name, "description": description}


def prompt_id() -> str:
    return input("Item id: ")


def show_items(items: list[dict]) -> None:
    if not items:
        print("(no items)")
        return
    for item in items:
        print(f"[{item['id']}] {item['name']} - {item['description']}")


def show_message(msg: str) -> None:
    print(msg)


def show_error(msg: str) -> None:
    print(f"Error: {msg}")


def clear_screen() -> None:
    print("\033[H\033[J", end="")
