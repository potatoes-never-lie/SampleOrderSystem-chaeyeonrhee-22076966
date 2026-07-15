from model.sample import Sample
from model.sample_id_format import format_sample_id

EXIT_CHOICE = "0"


class SampleController:
    def __init__(self, repository, view) -> None:
        self._repository = repository
        self._view = view

    def run(self) -> None:
        while True:
            choice = self._view.prompt_sample_menu()
            if choice == EXIT_CHOICE:
                return
            elif choice == "1":
                self._register_sample()
            elif choice == "2":
                self._list_samples()
            elif choice == "3":
                self._search_samples()
            else:
                self._view.show_error(f"Unknown option: {choice}")

    def _register_sample(self) -> None:
        data = self._view.prompt_sample_input()
        try:
            avg_production_time = float(data["avg_production_time"])
            yield_rate = float(data["yield_rate"])
        except ValueError:
            self._view.show_error("평균 생산시간과 수율은 숫자로 입력해야 합니다.")
            return
        if avg_production_time <= 0:
            self._view.show_error("평균 생산시간은 0보다 커야 합니다.")
            return
        if not (0 < yield_rate <= 1):
            self._view.show_error("수율은 0보다 크고 1 이하여야 합니다.")
            return
        if self._repository.get_by_name(data["name"]) is not None:
            self._view.show_error(f"이미 등록된 시료 이름입니다: {data['name']}")
            return
        sample = self._repository.add(
            Sample(
                id=None,
                name=data["name"],
                avg_production_time=avg_production_time,
                yield_rate=yield_rate,
                stock_qty=0,
            )
        )
        self._view.show_message(f"시료 등록 완료: [{format_sample_id(sample.id)}] {sample.name}")

    def _list_samples(self) -> None:
        self._view.show_samples(self._repository.list_all())

    def _search_samples(self) -> None:
        keyword = self._view.prompt_search_keyword()
        self._view.show_samples(self._repository.search_by_name(keyword))
