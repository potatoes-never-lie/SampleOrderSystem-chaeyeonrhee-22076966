# Phase 0 — 준비 (Preparation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이전 ConsoleMVC PoC 과제의 범용 `Item` 스켈레톤 중 더 이상 쓰이지 않는
코드(일반 CRUD 컨트롤러, 모니터, 메인 엔트리포인트)를 제거하고, 반도체 시료
생산주문관리 시스템 기능 명세(`PRD.md`)와 프로젝트 규칙(`CLAUDE.md`)을 문서화하여
Phase 1부터 시작할 도메인 개발의 기반을 마련한다.

**Architecture:** `model/`, `controller/`, `view/` 3개 패키지 구조는 그대로
유지한다. `SeedController`(및 그것이 의존하는 `model/item.py`, `model/repository.py`,
`view/console_view.py`, `seed.py`, `test_seed_controller.py`)는 더미 데이터 생성
도구로 계속 쓸 예정이라 이번엔 남겨두고, Phase 8에서 Sample/Order 도메인 기준으로
다시 작성한다. 그 외 `Item` 전용 코드(범용 CRUD 컨트롤러, 라이브 모니터, 구 메인
엔트리포인트)만 지운다. 문서는 저장소 루트에 `PRD.md`, `CLAUDE.md`로 추가한다.

**Tech Stack:** Python 3.13, pytest, git.

## Global Constraints

- 패키지 구조는 `model/ controller/ view/` 3-계층 MVC를 유지한다 (기존 스캐폴드 관례).
- 영속성은 Phase 1부터 SQLite로 고정한다 (Phase 0에서는 코드 삭제만, 신규 구현 없음).
- 생산 라인은 단일 라인 + FIFO 큐 + 백그라운드 스레드로 실시간 진행한다 (Phase 5 대상,
  Phase 0 문서에는 이 결정을 기록만 한다).
- 주문 상태 5종은 `RESERVED, REJECTED, PRODUCING, CONFIRMED, RELEASED` 로 표기를
  통일한다 (PDF 표는 `RELEASE`, 흐름도는 `RELEASED`로 표기가 엇갈려 있어 다른 상태값
  (`RESERVED/REJECTED/CONFIRMED`)과 동일하게 과거분사형인 `RELEASED`로 통일 — CLAUDE.md에
  이 결정을 명시한다).
- 커밋은 작업 단위(Task)별로 나눠서 수행한다.

---

### Task 1: 더 이상 쓰지 않는 Item 전용 코드 제거 (seed 도구는 보존)

**Files:**
- Delete: `controller/item_controller.py` (범용 CRUD 메뉴, Sample/Order 메뉴로 대체 예정)
- Delete: `controller/monitor_controller.py` (Item 목록 실시간 표시, Phase 6 모니터링으로 대체 예정)
- Delete: `main.py` (Item CRUD 콘솔 엔트리포인트, Phase 8에서 Sample/Order 메인 메뉴로 재작성)
- Delete: `monitor.py` (위 `monitor_controller.py`의 엔트리포인트)
- Delete: `conftest.py` (내용 없는 빈 파일, 필요 시 Phase 1에서 다시 생성)
- Keep (no change): `model/item.py`, `model/repository.py`, `view/console_view.py`,
  `controller/seed_controller.py`, `seed.py`, `test_seed_controller.py` — 더미 데이터
  생성 도구로 계속 쓰고, Phase 8에서 Sample/Order 도메인 기준으로 다시 작성한다.
- Keep (no change): `model/__init__.py`, `controller/__init__.py`, `view/__init__.py`, `.gitignore`

**Interfaces:**
- Consumes: 없음 (첫 작업)
- Produces: `model/sample.py`, `model/order.py`, `model/sample_repository.py`,
  `model/order_repository.py` 등 Phase 1 신규 파일이 들어갈 자리. 기존
  `model/item.py`/`model/repository.py`는 이름이 겹치지 않으므로 나란히 존재해도
  충돌 없다 (Phase 8에서 `SeedController`를 새 모델로 옮긴 뒤에만 최종 삭제).

- [ ] **Step 1: 삭제 대상 파일 목록 확인**

Run: `git -C "C:/reviewer/workspace/SampleOrderSystem" ls-files`
Expected output (관련 부분만 발췌):
```
.gitignore
conftest.py
controller/__init__.py
controller/item_controller.py
controller/monitor_controller.py
controller/seed_controller.py
docs/...
main.py
model/__init__.py
model/item.py
model/repository.py
monitor.py
seed.py
test_seed_controller.py
view/__init__.py
view/console_view.py
```

- [ ] **Step 2: 파일 삭제**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git rm controller/item_controller.py controller/monitor_controller.py \
  main.py monitor.py conftest.py
```

Expected: 각 파일에 대해 `rm '경로'` 출력, 총 5개 파일 삭제.

- [ ] **Step 3: 남은 구조 확인 및 seed 스크립트 동작 확인**

Run: `git -C "C:/reviewer/workspace/SampleOrderSystem" status`
Expected: `controller/item_controller.py`, `controller/monitor_controller.py`,
`main.py`, `monitor.py`, `conftest.py` 5개 파일이 `deleted:` 로 표시되고,
`model/item.py`, `model/repository.py`, `view/console_view.py`,
`controller/seed_controller.py`, `seed.py`, `test_seed_controller.py` 는 그대로
tracked 상태로 남는다.

Run: `cd "C:/reviewer/workspace/SampleOrderSystem" && python -m pytest test_seed_controller.py -v`
Expected: 3개 테스트 모두 `PASSED` (seed_controller.py가 여전히 정상 동작함을 확인).

Run: `python -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('C:/reviewer/workspace/SampleOrderSystem').rglob('*.py') if '.venv' not in str(p)]"`
Expected: 에러 없이 종료.

- [ ] **Step 4: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git commit -m "chore: remove unused Item CRUD/monitor entrypoints

Keeps model/item.py, model/repository.py, view/console_view.py and
SeedController/seed.py as the dummy-data tool (to be ported to the
Sample/Order domain in Phase 8) while dropping the generic Item CRUD
menu and live-monitor code that the sample-order system replaces."
```

---

### Task 2: `PRD.md` 작성

**Files:**
- Create: `PRD.md`

**Interfaces:**
- Consumes: 없음
- Produces: 이후 모든 Phase 계획 문서가 참조하는 기능 명세 원문 정리본.

- [ ] **Step 1: `PRD.md` 작성**

```markdown
# PRD — 반도체 시료 생산주문관리 시스템

## 1. 배경

가상의 반도체 회사 "S-Semi"는 다양한 반도체 시료(Sample)를 생산하여 연구소,
팹리스 업체, 대학 연구실 등에 납품한다. 시료는 주문이 들어오면 웨이퍼 공정
설비를 통해 제작되고, 검수를 거쳐 고객에게 출고된다. 기존에는 엑셀과
메모장으로 주문을 관리하여 재고·공정 현황 파악이 어려웠다. 이를 해결하기
위해 콘솔 기반의 "반도체 시료 생산주문관리 시스템"을 개발한다.

## 2. 역할

- **고객**: 필요한 시료를 이메일로 요청 (시스템 외부, 실제 입력은 주문 담당자가 대행)
- **주문 담당자**: 요청에 맞게 주문서(주문) 작성 — 시료 예약(RESERVED) 생성
- **생산 담당자**: 시료 등록, 주문 수신 후 승인/거절, 생산 라인 관리, 출고 처리

## 3. 시스템 개요

- 생산 라인은 공장에서 시료 하나를 생산하는 설비 흐름이며, 하나의 생산
  라인은 시료를 하나씩 순차 생산한다 (단일 라인, FIFO).
- 생산 라인은 주문이 들어온 시료에 대해서만 가동한다.
- 시스템은 콘솔 기반으로 동작하며, 담당자가 메뉴에서 명령을 입력해 시료
  등록과 주문 처리를 수행한다.

## 4. 주문 상태 흐름

| 상태 | 의미 |
|---|---|
| RESERVED | 주문 접수 |
| REJECTED | 주문 거절 (정상 흐름 밖의 상태, 모니터링 대상 제외) |
| PRODUCING | 주문 승인 완료, 재고 부족으로 생산 중 |
| CONFIRMED | 주문 승인 완료, 출고 대기 중 |
| RELEASED | 출고 완료 |

상태 전이:
```
RESERVED --거절--> REJECTED
RESERVED --승인, 재고 충분--> CONFIRMED
RESERVED --승인, 재고 부족--> PRODUCING --생산 완료--> CONFIRMED
CONFIRMED --출고 처리--> RELEASED
```

## 5. 메인 메뉴

기능별 선택 화면을 표시하고, 전체 시료에 대한 요약 정보(등록 시료 수, 총
재고, 전체 주문 수, 생산라인 대기 건수 등)를 함께 보여준다.

| 메뉴 | 의미 |
|---|---|
| 시료 관리 | 새로운 시료 등록, 목록 조회, 이름 검색 |
| 시료 주문 | 고객 주문 접수(RESERVED 생성) |
| 주문 승인/거절 | 생산 라인 담당자의 승인·거절 처리 |
| 모니터링 | 상태별 주문 수 및 시료별 재고 현황 확인 |
| 생산 라인 | 현재 생산 중인 시료 및 대기 중인 생산 큐 확인 |
| 출고 처리 | CONFIRMED 상태 주문에 대해 출고 실행 |

## 6. 시료 관리

시료(Sample)는 시스템의 가장 기본이 되는 단위이며, 등록된 시료만 주문
가능하다.

- **속성**: 시료 ID, 이름(고유), 평균 생산시간(min/ea), 수율, 현재 재고
- **수율**: (정상적인 시료 수 / 총 생산 시료 수). 예) 100개 생산 중 정상
  90개 = 0.9
- **시료 등록**: 위 속성 값을 입력받아 신규 시료를 추가한다.
- **시료 조회**: 등록된 모든 시료 목록과 현재 재고 수량을 표시한다.
- **시료 검색**: 이름 등 속성으로 특정 시료를 검색한다.

## 7. 시료 주문 (예약)

고객이 시료를 요청하면 주문 담당자가 주문을 생성한다.

- **입력 값**: 시료 ID, 고객명, 주문 수량
- 생성 즉시 주문 상태는 `RESERVED` 이다.

## 8. 주문 승인/거절

- **접수된 주문 목록**: `RESERVED` 상태의 주문 목록을 표시한다.
- **주문 승인**: 재고 상황에 따라 자동으로 분기한다.
  - 재고가 충분한 경우 → 즉시 `CONFIRMED` 로 전환
  - 재고가 부족한 경우 → 생산 라인(큐)에 자동 등록, `PRODUCING` 으로 전환
- **주문 거절**: 즉시 `REJECTED` 로 전환한다.

## 9. 모니터링

- **주문량 확인**: 상태별(`RESERVED/CONFIRMED/PRODUCING/RELEASED`) 주문 수를
  표시한다. `REJECTED`는 유효한 주문이 아니므로 집계에서 제외한다.
- **재고량 확인**: 시료별 현재 재고 수량과, 주문 대비 재고 수량에 따른 상태를
  함께 표시한다.
  - 여유: 주문 대비 재고 충분
  - 부족: 주문 대비 재고 수량 부족
  - 고갈: 재고 수량이 0

## 10. 생산 라인

- 주문량에 대한 부족분을 생산하되, 수율 및 오차를 고려하여 다음 공식으로
  계산한다.
  - 실 생산량 = `ceil(부족분 / 수율)`
  - 총 생산 시간 = `평균 생산시간 * 실 생산량`
- 생산 완료 시 주문 상태를 `PRODUCING → CONFIRMED` 로 변경하고, 재고에
  실 생산량을 가산한다.
- **생산 현황 표기**: 현재 생산 중인 시료에 대한 정보(주문 정보, 진행률 등)를
  표시한다.
- **대기 주문 확인**: 생산 큐에서 대기 중인 목록을 FIFO(선입선출) 순서로
  표시한다.

## 11. 출고 처리

- 재고가 충분해져 `CONFIRMED` 상태가 된 주문에 대해 출고를 실행한다.
- 출고 처리 시 주문 상태를 `RELEASED` 로 전환한다.

## 12. 비기능 요구사항 (본 프로젝트에서 결정한 사항)

- **영속성**: SQLite. 애플리케이션을 재실행해도 시료/주문 데이터가 유지되어야
  한다.
- **생산 라인 시간 흐름**: 백그라운드 스레드로 실시간 진행. 생산 시작 시각을
  기록하고 총 생산 시간이 경과하면 자동으로 완료 처리한다.
- **아키텍처**: Model / Controller / View 3-계층 구조를 유지한다.
```

- [ ] **Step 2: 마크다운 문법 확인**

Run: `python -c "import pathlib; print(len(pathlib.Path('C:/reviewer/workspace/SampleOrderSystem/PRD.md').read_text(encoding='utf-8')))"`
Expected: 파일이 존재하며 0보다 큰 문자 수 출력 (에러 없음).

- [ ] **Step 3: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add PRD.md
git commit -m "docs: add PRD.md for sample order system"
```

---

### Task 3: `CLAUDE.md` 작성

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: `PRD.md` (Task 2)의 상태 흐름·공식을 그대로 인용
- Produces: 이후 모든 Phase에서 Claude Code가 따라야 할 프로젝트 규칙 원천.

- [ ] **Step 1: `CLAUDE.md` 작성**

```markdown
# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code(및 협업자)를 위한 규칙을
정리한다. 기능 명세의 전체 내용은 `PRD.md`를 참조한다.

## 프로젝트 구조

- `model/` — 도메인 엔티티(dataclass)와 Repository(영속성 계층)
- `controller/` — 메뉴별 유스케이스 로직 (View와 Model을 연결)
- `view/` — 콘솔 입출력 전용, 비즈니스 로직 금지
- `docs/superpowers/specs/` — 설계 문서, `docs/superpowers/plans/` — 구현 계획
- 테스트 파일은 대상 모듈과 같은 계층에 `test_*.py` 로 둔다 (기존 관례:
  `test_seed_controller.py` 처럼 controller 이름 + `test_` 접두어).

## 도메인 규칙

### 엔티티

- **Sample**: `id, name(고유), avg_production_time(min/ea), yield_rate(0~1), stock_qty`
- **Order**: `id, sample_id, customer_name, qty, status, created_at`

### 주문 상태 (5종, `RELEASED`로 표기 통일)

| 상태 | 의미 |
|---|---|
| RESERVED | 주문 접수 |
| REJECTED | 주문 거절 (모니터링/집계 대상 제외) |
| PRODUCING | 승인 완료, 재고 부족으로 생산 중 |
| CONFIRMED | 승인 완료, 출고 대기 중 |
| RELEASED | 출고 완료 |

> PDF 원문은 흐름도에서 `RELEASED`, 표에서는 `RELEASE`로 표기가 엇갈린다.
> 다른 상태(`RESERVED/REJECTED/CONFIRMED`)와 동일한 과거분사형 패턴을
> 따르기 위해 이 프로젝트에서는 `RELEASED`로 통일한다.

허용된 전이만 구현한다:
```
RESERVED -> REJECTED
RESERVED -> CONFIRMED           (재고 충분)
RESERVED -> PRODUCING -> CONFIRMED   (재고 부족 -> 생산 완료)
CONFIRMED -> RELEASED
```
그 외 전이(예: REJECTED에서 재승인, RELEASED에서 재출고)는 에러로 처리한다.

### 생산 계산식

- 실 생산량 = `math.ceil(부족분 / 수율)`
- 총 생산 시간(분) = `평균 생산시간 * 실 생산량`
- 생산 큐는 FIFO. 생산 완료 시 재고에 실 생산량을 더하고 주문을
  `PRODUCING -> CONFIRMED` 로 전환한다.

## 기술 스택 / 컨벤션

- Python 3.13, 표준 라이브러리 `sqlite3`, `threading`, `queue`만 사용
  (외부 의존성 추가 전 표준 라이브러리로 해결 가능한지 먼저 검토).
- 엔티티는 `@dataclass`, 타입힌트 필수.
- Repository는 추상 베이스(ABC) + 구현체 패턴을 유지한다 (기존 `model/repository.py`
  관례 계승, 이번엔 SQLite 구현체 하나만 유지).
- 생산 라인 백그라운드 스레드는 `threading.Lock`으로 재고/큐 접근을 보호한다.

## 테스트 정책

- `pytest` 사용, TDD로 진행 (실패하는 테스트 먼저 작성 → 구현 → 통과 확인).
- Repository/Controller 단위 테스트를 우선하고, 마지막 Phase에서 접수→승인→
  생산→출고 전체 흐름의 엔드투엔드 테스트를 추가한다.

## 커밋 정책

- Phase별 계획 문서(`docs/superpowers/plans/`)의 Task 단위로 커밋한다.
- 커밋 메시지는 `feat:`, `fix:`, `docs:`, `chore:`, `test:` 접두어를 사용한다.

## 실행 방법 (Phase 1 이후 유효)

- `python main.py` — 콘솔 메인 메뉴 실행
- `pytest` — 전체 테스트 실행
```

- [ ] **Step 2: 커밋**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md project conventions"
```

---

### Task 4: 원격 푸시 및 최종 확인

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 커밋 로그 확인**

Run: `git -C "C:/reviewer/workspace/SampleOrderSystem" log --oneline`
Expected: 최소 4개 커밋 (초기 커밋 + Task1/2/3 커밋) 순서대로 표시.

- [ ] **Step 2: 원격 푸시**

```bash
cd "C:/reviewer/workspace/SampleOrderSystem"
git push origin master
```

Expected: `master -> master` 업데이트 성공 메시지.

- [ ] **Step 3: 최종 디렉터리 확인**

Run: `git -C "C:/reviewer/workspace/SampleOrderSystem" ls-files`
Expected:
```
.gitignore
CLAUDE.md
PRD.md
controller/__init__.py
controller/seed_controller.py
docs/superpowers/plans/2026-07-15-phase0-preparation.md
docs/superpowers/specs/2026-07-15-sample-order-system-plan.md
model/__init__.py
model/item.py
model/repository.py
seed.py
test_seed_controller.py
view/__init__.py
view/console_view.py
```
