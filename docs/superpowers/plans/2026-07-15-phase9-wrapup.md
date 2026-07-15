# Phase 9 — 마무리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or plain inline execution) to implement this plan task-by-task. No reviewer subagent is dispatched for this project — see project feedback memory. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이 저장소를 제출 가능한 상태로 마무리한다: Phase 8에서 `main.py`로
흡수되어 중복이 된 개별 메뉴 진입점을 정리하고, 테스트 커버리지 상태를
문서화하고, `README.md`를 작성하고, 커밋 이력을 확인한다.

**Architecture:** 새 기능은 없다. 삭제/문서화 위주의 마무리 작업이다.
`seed.py`/`monitor.py`는 `main.py`에 흡수되지 않는 독립 도구(더미데이터
생성, 실시간 데이터 조회)이므로 그대로 유지한다.

## Global Constraints

- 삭제 대상 파일이 다른 곳에서 import되지 않는지 삭제 전에 반드시 확인한다.
- 커밋 이력은 다시 쓰지 않는다(이미 원격에 푸시된 히스토리를 rebase/rewrite
  하지 않음) — 확인만 하고 필요하면 앞으로의 커밋 습관에 대한 메모만 남긴다.
- 이 프로젝트는 리뷰어 서브에이전트를 쓰지 않는다: 계획 확정 → 구현 → 테스트
  통과 확인 → 커밋 순으로 진행한다.

---

### Task 1: 통합 후 중복된 개별 메뉴 엔트리포인트 삭제

**Files:**
- Delete: `sample_menu.py`, `order_menu.py`, `approval_menu.py`,
  `monitoring_menu.py`, `production_line_menu.py`, `release_menu.py`
- Keep (no change): `seed.py`, `monitor.py` — `main.py`에 흡수되지 않는
  독립 도구(더미데이터 생성 / 실시간 데이터 조회)이므로 유지.

**Interfaces:**
- Consumes: 없음
- Produces: 없음 (정리 전용). `main.py`가 6개 컨트롤러 전체를 이미 통합
  제공하므로 개별 진입점은 더 이상 필요하지 않다.

- [ ] **Step 1: 삭제 대상이 다른 곳에서 참조되지 않는지 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && grep -rln "sample_menu\|order_menu\|approval_menu\|monitoring_menu\|production_line_menu\|release_menu" --include="*.py" . | grep -v .venv`
Expected: 삭제 대상 파일 6개 자기 자신 외에는 아무 것도 출력되지 않음
(테스트 코드나 다른 스크립트가 이 파일들을 import하지 않음을 확인).

- [ ] **Step 2: 파일 삭제**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git rm sample_menu.py order_menu.py approval_menu.py monitoring_menu.py production_line_menu.py release_menu.py
```

Expected: 6개 파일에 대해 `rm '경로'` 출력.

- [ ] **Step 3: 전체 테스트 스위트 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 기존 77개 테스트 모두 `PASSED` (삭제한 파일들은 애초에 테스트
대상이 아니었으므로 개수 변화 없음).

- [ ] **Step 4: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git commit -m "chore: remove per-controller menu entrypoints superseded by main.py

sample_menu.py, order_menu.py, approval_menu.py, monitoring_menu.py,
production_line_menu.py, and release_menu.py were temporary
single-controller entrypoints used during Phase 2-7 development.
main.py (Phase 8) now wires all six controllers behind one main menu,
so these are dead duplicate code. seed.py and monitor.py are kept —
they are standalone tools main.py does not absorb."
```

---

### Task 2: 테스트 커버리지 감사를 `CLAUDE.md`에 기록

**Files:**
- Modify: `CLAUDE.md` (섹션 추가, 기존 내용은 그대로 유지)

**Interfaces:**
- Consumes: 없음
- Produces: `CLAUDE.md`에 감사 결과 섹션 추가. 코드 변경 없음.

- [ ] **Step 1: 소스 모듈 ↔ 테스트 파일 대응表 확인**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && ls model/*.py controller/*.py view/*.py`
Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && ls test_*.py`

각 `model/*.py`, `controller/*.py` 파일에 대해 대응하는 `test_*.py`가
있는지 아래 표와 대조 확인한다 (이미 Phase 1~8에서 전부 만들어졌으므로
새로 작성할 테스트는 없다 — 유일한 의도적 예외는 `view/console_view.py`).

- [ ] **Step 2: `CLAUDE.md`에 감사 결과 섹션 추가**

`## 실행 방법` 섹션 뒤에 이어서 추가:

```markdown
## 테스트 커버리지 감사 (Phase 9)

모든 `model/*.py`, `controller/*.py` 모듈은 대응하는 `test_*.py`를 가진다:

| 모듈 | 테스트 |
|---|---|
| `model/sample_repository.py` | `test_sample_repository.py` |
| `model/sample_id_format.py` | `test_sample_id_format.py` |
| `model/order_repository.py` | `test_order_repository.py` |
| `model/production_queue_repository.py` | `test_production_queue_repository.py` |
| `controller/sample_controller.py` | `test_sample_controller.py` |
| `controller/order_controller.py` | `test_order_controller.py` |
| `controller/approval_controller.py` | `test_approval_controller.py` |
| `controller/production_line_worker.py` | `test_production_line_worker.py` |
| `controller/production_line_controller.py` | `test_production_line_controller.py` |
| `controller/monitoring_controller.py` | `test_monitoring_controller.py` |
| `controller/release_controller.py` | `test_release_controller.py` |
| `controller/main_menu_controller.py` | `test_main_menu_controller.py` |
| `controller/live_monitor_controller.py` | `test_live_monitor_controller.py` |
| `controller/seed_controller.py` | `test_seed_controller.py` |
| 전체 통합 흐름 | `test_end_to_end_order_flow.py` |

`model/sample.py`, `model/order.py`, `model/production_job.py`는 순수
dataclass/Enum이라 별도 테스트 없이 위 리포지토리 테스트들이 간접적으로
검증한다.

**의도적으로 테스트하지 않은 부분:** `view/console_view.py`는 `print`/`input`
호출만 있는 순수 I/O 계층이라 직접 단위 테스트가 없다 — 모든 컨트롤러
테스트가 view를 페이크로 교체해 호출 여부만 검증하고, 실제 콘솔 출력
포맷은 수동 확인 대상으로 남긴다. 이 계층에 조건 분기나 계산 로직이
추가되면 그때 테스트를 추가한다.
```

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add CLAUDE.md
git commit -m "docs: record test coverage audit in CLAUDE.md"
```

---

### Task 3: `README.md` 작성

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: 없음
- Produces: 저장소 루트의 `README.md` — 프로젝트 소개/실행 방법을 다룬다
  (기능 명세 원문은 `PRD.md`, 개발 규칙은 `CLAUDE.md`가 이미 다룬다).

- [ ] **Step 1: `README.md` 작성**

```markdown
# 반도체 시료 생산주문관리 시스템

콘솔 기반으로 반도체 시료(Sample)의 등록/주문/승인/생산/출고를 관리하는
시스템. 기능 명세는 [`PRD.md`](PRD.md), 개발 규칙은 [`CLAUDE.md`](CLAUDE.md)
참고.

## 실행 방법

```bash
python main.py
```

메인 메뉴에서 시료 관리 / 시료 주문 / 주문 승인·거절 / 모니터링 /
생산라인 조회 / 출고 처리를 선택해 사용한다. 데이터는 `data/sampleorder.db`
(SQLite)에 저장되어 재실행해도 유지된다.

생산 라인은 백그라운드 스레드로 동작하며, 시뮬레이션 1분당 실제 대기
시간은 `PRODUCTION_TIME_SCALE` 환경변수로 조절한다 (기본값 `1.0` = 60배
가속, `60`을 주면 실제 시간 그대로 흐름):

```bash
PRODUCTION_TIME_SCALE=60 python main.py
```

## 더미 데이터 생성

```bash
python seed.py
```

랜덤 시료 10종과 주문 20건(`RESERVED` 상태)을 DB에 추가한다.

## 실시간 데이터 조회 도구

```bash
python monitor.py
```

2초 간격으로 전체 시료/주문 현황을 콘솔에 출력한다 (`Ctrl+C`로 종료).

## 테스트

```bash
pytest
```

## 프로젝트 구조

- `model/` — 도메인 엔티티(`Sample`, `Order`, `ProductionJob`)와 SQLite Repository
- `controller/` — 메뉴별 유스케이스 로직 (`SampleController`, `OrderController`,
  `ApprovalController`, `ProductionLineWorker`/`ProductionLineController`,
  `MonitoringController`, `ReleaseController`, `MainMenuController`,
  `SeedController`, `LiveMonitorController`)
- `view/` — 콘솔 입출력 전용 (`console_view.py`)
- `docs/superpowers/` — 설계 문서(`specs/`)와 Phase별 구현 계획(`plans/`)
```

- [ ] **Step 2: 마크다운 문법 확인**

Run: `python -c "import pathlib; print(len(pathlib.Path('C:/reviewer/workspace/SampleOrderSystem/README.md').read_text(encoding='utf-8')))"`
Expected: 0보다 큰 문자 수 출력 (에러 없음).

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add README.md
git commit -m "docs: add README.md with run/test instructions"
```

---

### Task 4: 커밋 이력 확인 및 최종 검증/푸시

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 커밋 이력 확인 (다시 쓰지 않음, 읽기만)**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && git log --oneline`
확인할 것: 각 Phase가 `Add Phase N implementation plan` → 기능/테스트
커밋(`feat:`/`fix:`/`refactor:`/`test:`/`chore:`) → 다음 Phase 순으로
이어지는지, 커밋 메시지가 "왜"를 설명하는지. 문제가 될 만한 것이 보이면
(예: 의미 없는 메시지) 결과를 사용자에게 보고만 하고 임의로 rebase하지
않는다 — 이미 원격에 푸시된 히스토리이므로 재작성은 사용자 승인 없이
하지 않는다.

- [ ] **Step 2: 전체 테스트 스위트 최종 실행**

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest -v`
Expected: 77개 테스트 모두 `PASSED`.

- [ ] **Step 3: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.
