from model.order import Order, OrderStatus
from model.sample_id_format import parse_sample_id

EXIT_CHOICE = "0"


class OrderController:
    def __init__(self, order_repository, sample_repository, view) -> None:
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_order_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._reserve_order()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _reserve_order(self) -> None:
        data = self._view.prompt_order_input()

        sample_id = parse_sample_id(data["sample_id"])
        if sample_id is None:
            self._view.show_error(f"유효한 시료 ID 형식이 아닙니다: {data['sample_id']}")
            return
        sample = self._sample_repository.get(sample_id)
        if sample is None:
            self._view.show_error(f"존재하지 않는 시료 ID입니다: {data['sample_id']}")
            return

        try:
            qty = int(data["qty"])
        except ValueError:
            self._view.show_error("주문 수량은 숫자로 입력해야 합니다.")
            return
        if qty <= 0:
            self._view.show_error("주문 수량은 0보다 커야 합니다.")
            return

        customer_name = data["customer_name"].strip()
        if not customer_name:
            self._view.show_error("고객명을 입력해야 합니다.")
            return

        order = self._order_repository.add(
            Order(
                id=None,
                order_no=None,
                sample_id=sample_id,
                customer_name=customer_name,
                qty=qty,
                status=OrderStatus.RESERVED,
                created_at=None,
            )
        )
        self._view.show_message(f"예약 접수 완료: {order.order_no} (상태: {order.status.value})")
