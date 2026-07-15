import math

from model.order import OrderStatus
from model.production_job import ProductionJob

EXIT_CHOICE = "0"


class ApprovalController:
    def __init__(self, order_repository, sample_repository, production_queue_repository, view) -> None:
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._production_queue_repository = production_queue_repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_approval_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._process_approval()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _process_approval(self) -> None:
        reserved_orders = self._order_repository.list_by_status(OrderStatus.RESERVED)
        if not reserved_orders:
            self._view.show_message("대기 중인 주문이 없습니다.")
            return

        self._view.show_order_list(reserved_orders)
        selection = self._view.prompt_order_selection(len(reserved_orders))
        if not isinstance(selection, int) or not (1 <= selection <= len(reserved_orders)):
            self._view.show_error("잘못된 번호입니다.")
            return
        order = reserved_orders[selection - 1]

        decision = self._view.prompt_approval_decision().strip().upper()
        if decision == "Y":
            self._approve(order)
        elif decision == "N":
            self._reject(order)
        else:
            self._view.show_error("Y 또는 N을 입력해야 합니다.")

    def _approve(self, order) -> None:
        sample = self._sample_repository.get(order.sample_id)
        if sample.stock_qty >= order.qty:
            self._sample_repository.update_stock(sample.id, -order.qty)
            updated = self._order_repository.update_status(order.id, OrderStatus.CONFIRMED)
            self._view.show_message(f"승인 완료: {updated.order_no} (상태: {updated.status.value})")
            return

        shortage = order.qty - sample.stock_qty
        actual_qty = math.ceil(shortage / sample.yield_rate)
        total_time = sample.avg_production_time * actual_qty
        self._production_queue_repository.enqueue(
            ProductionJob(
                id=None,
                order_id=order.id,
                shortage_qty=shortage,
                actual_qty=actual_qty,
                total_time=total_time,
                created_at=None,
            )
        )
        updated = self._order_repository.update_status(order.id, OrderStatus.PRODUCING)
        self._view.show_message(
            f"재고 부족으로 생산 등록: {updated.order_no} (상태: {updated.status.value}, "
            f"실생산량 {actual_qty}ea, 예상 생산시간 {total_time:.1f}min)"
        )

    def _reject(self, order) -> None:
        updated = self._order_repository.update_status(order.id, OrderStatus.REJECTED)
        self._view.show_message(f"거절 처리: {updated.order_no} (상태: {updated.status.value})")
