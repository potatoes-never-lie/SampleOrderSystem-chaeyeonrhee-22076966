from model.order import OrderStatus

EXIT_CHOICE = "0"


class ReleaseController:
    def __init__(self, order_repository, view) -> None:
        self._order_repository = order_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_release_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._process_release()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _process_release(self) -> None:
        confirmed_orders = self._order_repository.list_by_status(OrderStatus.CONFIRMED)
        if not confirmed_orders:
            self._view.show_message("출고 가능한 주문이 없습니다.")
            return

        self._view.show_order_list(confirmed_orders)
        selection = self._view.prompt_order_selection(len(confirmed_orders))
        if not isinstance(selection, int) or not (1 <= selection <= len(confirmed_orders)):
            self._view.show_error("잘못된 번호입니다.")
            return
        order = confirmed_orders[selection - 1]

        updated = self._order_repository.update_status(order.id, OrderStatus.RELEASED)
        self._view.show_message(f"출고 처리 완료: {updated.order_no} (상태: {updated.status.value})")
