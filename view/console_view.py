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


ORDER_MENU_TEXT = """
1. 시료 주문
0. 뒤로
"""


def prompt_order_menu() -> str:
    print(ORDER_MENU_TEXT)
    return input("선택 > ")


def prompt_order_input() -> dict:
    sample_id = input("시료 ID: ")
    customer_name = input("고객명: ")
    qty = input("주문 수량: ")
    return {"sample_id": sample_id, "customer_name": customer_name, "qty": qty}


APPROVAL_MENU_TEXT = """
1. 주문 승인/거절
0. 뒤로
"""


def prompt_approval_menu() -> str:
    print(APPROVAL_MENU_TEXT)
    return input("선택 > ")


def show_order_list(orders: list) -> None:
    for idx, order in enumerate(orders, start=1):
        print(
            f"[{idx}] {order.order_no} | 시료 {format_sample_id(order.sample_id)} "
            f"| 고객 {order.customer_name} | 수량 {order.qty}ea | 상태 {order.status.value}"
        )


def prompt_order_selection(count: int) -> int | None:
    raw = input(f"승인/거절할 번호 (1-{count}) > ")
    try:
        return int(raw)
    except ValueError:
        return None


def prompt_approval_decision() -> str:
    return input("[Y] 승인  [N] 거절 > ")


PRODUCTION_MENU_TEXT = """
1. 생산 라인 조회
0. 뒤로
"""


def prompt_production_menu() -> str:
    print(PRODUCTION_MENU_TEXT)
    return input("선택 > ")


def show_production_status(job, order, sample, progress: float) -> None:
    print(
        f"주문번호 {order.order_no} | 시료 {format_sample_id(sample.id)} {sample.name} "
        f"| 부족분 {job.shortage_qty}ea → 실생산량 {job.actual_qty}ea "
        f"| 진행률 {progress * 100:.0f}%"
    )


def show_pending_queue(entries: list) -> None:
    if not entries:
        print("(대기 중인 생산 작업 없음)")
        return
    for idx, (job, order) in enumerate(entries, start=1):
        print(
            f"[{idx}] 주문번호 {order.order_no} | 부족분 {job.shortage_qty}ea "
            f"| 실생산량 {job.actual_qty}ea | 예상소요 {job.total_time:.1f}min"
        )


MONITOR_MENU_TEXT = """
1. 주문량 확인
2. 재고량 확인
0. 뒤로
"""


def prompt_monitor_menu() -> str:
    print(MONITOR_MENU_TEXT)
    return input("선택 > ")


def show_order_counts(counts: list) -> None:
    for status, count in counts:
        print(f"{status.value}: {count}건")


def show_inventory_status(entries: list) -> None:
    for sample, demand, state in entries:
        print(
            f"[{format_sample_id(sample.id)}] {sample.name} | 재고 {sample.stock_qty}ea "
            f"| 주문대비 수요 {demand}ea | 상태 {state}"
        )


RELEASE_MENU_TEXT = """
1. 출고 처리
0. 뒤로
"""


def prompt_release_menu() -> str:
    print(RELEASE_MENU_TEXT)
    return input("선택 > ")
