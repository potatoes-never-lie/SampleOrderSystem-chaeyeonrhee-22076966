from model.sample_id_format import format_sample_id

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


SAMPLE_MENU_TEXT = """
1. 시료 등록
2. 시료 조회
3. 시료 검색
0. 뒤로
"""


def prompt_sample_menu() -> str:
    print(SAMPLE_MENU_TEXT)
    return input("선택 > ")


def prompt_sample_input() -> dict:
    name = input("이름: ")
    avg_production_time = input("평균 생산시간(min/ea): ")
    yield_rate = input("수율(0~1): ")
    return {"name": name, "avg_production_time": avg_production_time, "yield_rate": yield_rate}


def prompt_search_keyword() -> str:
    return input("검색어(이름 또는 시료 ID): ")


def show_samples(samples: list) -> None:
    if not samples:
        print("(등록된 시료 없음)")
        return
    for sample in samples:
        print(
            f"[{format_sample_id(sample.id)}] {sample.name} | 평균생산시간 {sample.avg_production_time}min/ea "
            f"| 수율 {sample.yield_rate} | 재고 {sample.stock_qty}ea"
        )
