# Phase 2 — 시료 관리 기능 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or plain inline execution) to implement this plan task-by-task. No reviewer subagent is dispatched for this project — see project feedback memory. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 콘솔에서 시료를 등록/조회/검색할 수 있는 `SampleController`와 그에 필요한
콘솔 뷰 함수를 추가한다. Phase 1에서 만든 `Sample`/`SqliteSampleRepository`를
그대로 사용하되, `search_by_name`을 이름뿐 아니라 시료 ID(`S-001` 형식)로도
검색되도록 확장한다. 시료 ID의 `S-001` 표시/파싱은 공용 유틸로 분리해 검색과
이후 Phase 3(주문 접수)에서도 재사용한다.

**Architecture:** 기존 `controller/`, `view/` 관례를 그대로 따른다.
`model/sample_id_format.py`에 "S-001" ↔ 정수 id 변환을 담당하는 순수 함수
2개를 두고, **Repository 계층(`model/sample_repository.py`)의 `search_by_name`을
직접 확장**해서 이름 부분일치 또는 시료 ID 일치를 SQL 한 번으로 처리한다
(컨트롤러에서 결과를 합치지 않는다). `controller/sample_controller.py`는
`SampleRepository`(ABC 타입)와 `view` 모듈을 주입받아 동작하는 얇은
유스케이스 계층이다. `view/console_view.py`에 시료 메뉴용 입출력 함수를
추가하고, 기존 `seed.py`처럼 단독 실행 진입점 `sample_menu.py`도 추가한다
(Phase 8에서 통합 `main.py`로 흡수될 임시 진입점).

**Tech Stack:** Python 3.13 표준 라이브러리 `re`, pytest, 기존
`model.sample`/`model.sample_repository` (Phase 1 산출물, 이번 Phase에서
`search_by_name`만 확장).

## Global Constraints

- Repository는 Phase 1의 `SqliteSampleRepository`를 그대로 쓰되, **`search_by_name`
  메서드 하나만 확장**한다 (스키마 변경 없음, 다른 메서드는 그대로 유지).
- **시료 ID 표기/파싱**: 저장은 정수 autoincrement PK 그대로 두고, 화면 표시와
  사용자 입력 파싱만 `model/sample_id_format.py`의 `format_sample_id(id) -> str`
  (`"S-{id:03d}"`)과 `parse_sample_id(text) -> int | None`(`"S-003"`, `"S003"`,
  `"3"` 등 대소문자·대시 유무 관계없이 정수로 변환, 매칭 실패 시 `None`)으로 처리한다.
  이 유틸은 Repository의 확장된 검색과 Phase 3(주문 접수에서 사용자가 시료 ID를
  입력)에서 그대로 재사용한다.
- **검색 확장**: `search_by_name(keyword)`는 이제 (1) `name` 부분일치 **OR**
  (2) `keyword`가 `parse_sample_id`로 파싱되는 경우 그 id와 일치, 두 조건을
  SQL `OR`로 한 번에 검색해 결과에 중복이 생기지 않도록 한다. 컨트롤러는 이
  메서드를 그대로 호출하기만 하면 된다 (컨트롤러 쪽에서 별도로 합치지 않음).
- 시료 등록 입력 검증(신뢰 경계 지점): `avg_production_time > 0`, `0 < yield_rate <= 1`,
  이름 중복 불가(`get_by_name` 사용). 숫자가 아닌 입력은 에러 처리.
- 컨트롤러/레포지토리 테스트는 Phase 1과 동일하게 실제 SQLite(`tmp_path`)를 쓰고,
  컨트롤러 테스트의 view만 기록용 페이크로 대체한다 (레포지토리 mock 금지).
- 컨트롤러의 개별 동작 메서드(`_register_sample` 등)를 직접 호출해서 테스트하고,
  `run()`의 메뉴 루프 자체는 단순 분기라 별도 테스트하지 않는다.
- 이 프로젝트는 리뷰어 서브에이전트를 쓰지 않는다: 계획 확정 → 구현 → 테스트
  통과 확인 → 커밋 순으로 진행한다.

---

### Task 1: 시료 ID 표시/파싱 유틸

**Files:**
- Create: `model/sample_id_format.py`
- Test: `test_sample_id_format.py`

**Interfaces:**
- Consumes: 없음
- Produces: `format_sample_id(sample_id: int) -> str`,
  `parse_sample_id(text: str) -> int | None`. Task 2(Repository 검색 확장),
  Task 3(`SampleController`/뷰), Phase 3(주문 접수)이 그대로 가져다 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성 — `test_sample_id_format.py`**

```python
from model.sample_id_format import format_sample_id, parse_sample_id


def test_format_sample_id_pads_to_three_digits():
    assert format_sample_id(1) == "S-001"
    assert format_sample_id(42) == "S-042"
    assert format_sample_id(1234) == "S-1234"


def test_parse_sample_id_accepts_dash_format():
    assert parse_sample_id("S-003") == 3


def test_parse_sample_id_accepts_lowercase_and_no_dash():
    assert parse_sample_id("s003") == 3


def test_parse_sample_id_accepts_plain_digits():
    assert parse_sample_id("3") == 3


def test_parse_sample_id_strips_surrounding_whitespace():
    assert parse_sample_id("  S-003  ") == 3


def test_parse_sample_id_returns_none_for_non_matching_text():
    assert parse_sample_id("실리콘") is None
    assert parse_sample_id("") is None
    assert parse_sample_id("S-") is None
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_sample_id_format.py -v`
Expected: `ModuleNotFoundError: No module named 'model.sample_id_format'` 로 전부 실패.

- [ ] **Step 3: `model/sample_id_format.py` 구현**

```python
import re

_SAMPLE_ID_PATTERN = re.compile(r"^s-?(\d+)$", re.IGNORECASE)


def format_sample_id(sample_id: int) -> str:
    return f"S-{sample_id:03d}"


def parse_sample_id(text: str) -> int | None:
    stripped = text.strip()
    match = _SAMPLE_ID_PATTERN.match(stripped)
    if match:
        return int(match.group(1))
    if stripped.isdigit():
        return int(stripped)
    return None
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_sample_id_format.py -v`
Expected: 6개 테스트 모두 `PASSED`.

- [ ] **Step 5: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add model/sample_id_format.py test_sample_id_format.py
git commit -m "feat: add sample id display/parse helpers"
```

---

### Task 2: `search_by_name`을 시료 ID 검색까지 지원하도록 확장

**Files:**
- Modify: `model/sample_repository.py` (`search_by_name` 메서드만 변경)
- Modify: `test_sample_repository.py` (테스트 추가)

**Interfaces:**
- Consumes: `model.sample_id_format.parse_sample_id` (Task 1 산출물)
- Produces: `SampleRepository.search_by_name(keyword: str) -> list[Sample]`의
  동작 변경 — 이름 부분일치 OR 시료 ID 일치. 시그니처는 그대로이므로 Task 3의
  `SampleController`는 이 메서드를 그대로 호출하기만 하면 된다.

- [ ] **Step 1: 실패하는 테스트 추가 — `test_sample_repository.py`에 이어서 작성**

```python
def test_search_by_name_matches_sample_id_dash_format(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="실리콘 웨이퍼-8인치", avg_production_time=0.5, yield_rate=0.92, stock_qty=0))
    target = repo.add(Sample(id=None, name="포토레지스트-PR7", avg_production_time=0.2, yield_rate=0.95, stock_qty=0))

    results = repo.search_by_name(f"S-{target.id:03d}")

    assert [s.id for s in results] == [target.id]


def test_search_by_name_matches_plain_numeric_id(tmp_path):
    repo = _repo(tmp_path)
    target = repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))

    results = repo.search_by_name(str(target.id))

    assert [s.id for s in results] == [target.id]


def test_search_by_name_does_not_duplicate_when_name_and_id_both_match(tmp_path):
    repo = _repo(tmp_path)
    sample = repo.add(Sample(id=None, name="1", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))

    results = repo.search_by_name("1")

    assert len(results) == 1
    assert results[0].id == sample.id


def test_search_by_name_still_matches_partial_name_when_not_an_id(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="산화막 웨이퍼-SiO2", avg_production_time=0.6, yield_rate=0.88, stock_qty=0))

    results = repo.search_by_name("웨이퍼")

    assert len(results) == 1
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_sample_repository.py -v`
Expected: 새로 추가한 4개 테스트 중 `test_search_by_name_matches_sample_id_dash_format`,
`test_search_by_name_matches_plain_numeric_id`가 `FAILED` (아직 이름만 검색하므로
ID로는 못 찾음). 나머지 기존 테스트는 계속 `PASSED`.

- [ ] **Step 3: `search_by_name` 확장 구현**

`model/sample_repository.py` 상단 import에 추가:

```python
from model.sample_id_format import parse_sample_id
```

기존 `search_by_name` 메서드를 아래로 교체:

```python
    def search_by_name(self, keyword: str) -> list[Sample]:
        sample_id = parse_sample_id(keyword)
        if sample_id is not None:
            rows = self._conn.execute(
                "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples "
                "WHERE name LIKE ? OR id = ?",
                (f"%{keyword}%", sample_id),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, name, avg_production_time, yield_rate, stock_qty FROM samples WHERE name LIKE ?",
                (f"%{keyword}%",),
            ).fetchall()
        return [Sample(*row) for row in rows]
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_sample_repository.py -v`
Expected: 기존 8개 + 신규 4개 = 12개 모두 `PASSED`.

- [ ] **Step 5: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add model/sample_repository.py test_sample_repository.py
git commit -m "feat: extend Sample search to match by sample id"
```

---

### Task 3: `SampleController` + 콘솔 뷰 확장

**Files:**
- Modify: `view/console_view.py` (함수 추가, 기존 함수는 그대로 유지)
- Create: `controller/sample_controller.py`
- Test: `test_sample_controller.py`

**Interfaces:**
- Consumes: `model.sample.Sample`, `model.sample_repository.SqliteSampleRepository`
  (Task 2에서 검색이 확장된 상태), `model.sample_id_format.format_sample_id`
  (Task 1 산출물)
- Produces: `SampleController(repository: SampleRepository, view) -> None`,
  공개 메서드 `run()`. `view` 프로토콜에 다음 함수가 필요:
  `prompt_sample_menu() -> str`, `prompt_sample_input() -> dict`,
  `prompt_search_keyword() -> str`, `show_samples(samples: list[Sample]) -> None`,
  `show_message(msg: str) -> None`, `show_error(msg: str) -> None`
  (뒤 두 개는 `console_view.py`에 이미 존재).

- [ ] **Step 1: `view/console_view.py`에 시료 메뉴 함수 추가**

파일 상단 import 구역에 추가:

```python
from model.sample_id_format import format_sample_id
```

파일 끝에 이어서 추가:

```python
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
```

- [ ] **Step 2: 실패하는 테스트 작성 — `test_sample_controller.py`**

```python
from model.sample import Sample
from model.sample_repository import SqliteSampleRepository
from model.sample_id_format import format_sample_id
from controller.sample_controller import SampleController


class _FakeView:
    def __init__(self, sample_input=None, search_keyword=None):
        self.messages = []
        self.errors = []
        self.shown_samples = None
        self._sample_input = sample_input
        self._search_keyword = search_keyword

    def prompt_sample_input(self):
        return self._sample_input

    def prompt_search_keyword(self):
        return self._search_keyword

    def show_samples(self, samples):
        self.shown_samples = samples

    def show_message(self, msg):
        self.messages.append(msg)

    def show_error(self, msg):
        self.errors.append(msg)


def _repo(tmp_path):
    return SqliteSampleRepository(str(tmp_path / "test.db"))


def test_register_sample_adds_to_repository(tmp_path):
    repo = _repo(tmp_path)
    view = _FakeView(sample_input={"name": "실리콘 웨이퍼-8인치", "avg_production_time": "0.5", "yield_rate": "0.92"})
    controller = SampleController(repo, view)

    controller._register_sample()

    samples = repo.list_all()
    assert len(samples) == 1
    assert samples[0].name == "실리콘 웨이퍼-8인치"
    assert samples[0].stock_qty == 0
    assert view.messages == [f"시료 등록 완료: [{format_sample_id(samples[0].id)}] 실리콘 웨이퍼-8인치"]


def test_register_sample_rejects_duplicate_name(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=0))
    view = _FakeView(sample_input={"name": "A", "avg_production_time": "0.2", "yield_rate": "0.8"})
    controller = SampleController(repo, view)

    controller._register_sample()

    assert len(repo.list_all()) == 1
    assert view.errors == ["이미 등록된 시료 이름입니다: A"]


def test_register_sample_rejects_non_numeric_input(tmp_path):
    repo = _repo(tmp_path)
    view = _FakeView(sample_input={"name": "A", "avg_production_time": "빠름", "yield_rate": "0.9"})
    controller = SampleController(repo, view)

    controller._register_sample()

    assert repo.list_all() == []
    assert view.errors == ["평균 생산시간과 수율은 숫자로 입력해야 합니다."]


def test_register_sample_rejects_yield_rate_out_of_range(tmp_path):
    repo = _repo(tmp_path)
    view = _FakeView(sample_input={"name": "A", "avg_production_time": "0.5", "yield_rate": "1.5"})
    controller = SampleController(repo, view)

    controller._register_sample()

    assert repo.list_all() == []
    assert view.errors == ["수율은 0보다 크고 1 이하여야 합니다."]


def test_list_samples_shows_all_registered(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="A", avg_production_time=0.1, yield_rate=0.9, stock_qty=5))
    repo.add(Sample(id=None, name="B", avg_production_time=0.2, yield_rate=0.8, stock_qty=10))
    view = _FakeView()
    controller = SampleController(repo, view)

    controller._list_samples()

    assert {s.name for s in view.shown_samples} == {"A", "B"}


def test_search_samples_delegates_to_repository_search(tmp_path):
    repo = _repo(tmp_path)
    repo.add(Sample(id=None, name="실리콘 웨이퍼-8인치", avg_production_time=0.5, yield_rate=0.92, stock_qty=0))
    target = repo.add(Sample(id=None, name="포토레지스트-PR7", avg_production_time=0.2, yield_rate=0.95, stock_qty=0))
    view = _FakeView(search_keyword=format_sample_id(target.id))
    controller = SampleController(repo, view)

    controller._search_samples()

    assert [s.id for s in view.shown_samples] == [target.id]
```

(참고: `search_by_name`이 이름과 ID를 모두 검색하도록 Task 2에서 이미
확장되었으므로, `SampleController._search_samples`는 결과를 직접 조합하지
않고 리포지토리 호출 결과를 그대로 `view.show_samples`에 넘기기만 한다.)

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_sample_controller.py -v`
Expected: `ModuleNotFoundError: No module named 'controller.sample_controller'` 로 전부 실패.

- [ ] **Step 4: `controller/sample_controller.py` 구현**

```python
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
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_sample_controller.py -v`
Expected: 7개 테스트 모두 `PASSED`.

- [ ] **Step 6: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add view/console_view.py controller/sample_controller.py test_sample_controller.py
git commit -m "feat: add SampleController for register/list/search"
```

---

### Task 4: 단독 실행 진입점 `sample_menu.py`

**Files:**
- Create: `sample_menu.py`

**Interfaces:**
- Consumes: `controller.sample_controller.SampleController`,
  `model.sample_repository.SqliteSampleRepository`, `view.console_view`
- Produces: 없음 (Phase 8에서 통합 `main.py`가 이 컨트롤러를 메뉴 중 하나로 흡수)

- [ ] **Step 1: `sample_menu.py` 작성**

```python
from controller.sample_controller import SampleController
from model.sample_repository import SqliteSampleRepository
from view import console_view

if __name__ == "__main__":
    SampleController(SqliteSampleRepository(), console_view).run()
```

- [ ] **Step 2: 수동 스모크 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -c "import ast; ast.parse(open('sample_menu.py', encoding='utf-8').read())"`
Expected: 에러 없이 종료 (문법 확인, 대화형 입력이 필요한 실제 실행은 생략).

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add sample_menu.py
git commit -m "feat: add standalone sample_menu.py entrypoint"
```

---

### Task 5: 전체 검증 및 푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 16개(Phase 1) + 신규(`test_sample_id_format.py` 6개 +
`test_sample_repository.py` 신규 4개 + `test_sample_controller.py` 7개) =
총 33개 모두 `PASSED`.

- [ ] **Step 2: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
