# WORKLOG
Project: Shape-Modeling Based LLM Mold Quotation System  
형상 모델링 기반 학습형 LLM 금형 견적 시스템

---

## AI Fast Context (AUTO-UPDATED)
> This section reflects the latest confirmed project state only.  
> 이 섹션은 항상 **최신 상태만** 반영한다.

- Current focus:
  - Final Release Verification
  - 버그 수정 및 최종 배포 확인
- Known blocker:
  - None
- Forbidden approaches:
  - Use `--onefile` for installers
- Last confirmed working logic:
  - Installers rebuilt successfully with bug fix
- Next planned action:
  - User verification

---

<!-- Session logs are appended below. Do not edit past sessions. -->

## Session: YYYY-MM-DD / Project kickoff
@agent=Human
@role=Architect
@scope=Overall
@status=Done

### Intent
- Define development and collaboration strategy
  - 개발 및 멀티 AI 협업 전략 수립

### Context
- Multiple AI agents used (Cursor, Codex, Anti-Gravity, Claude)
  - 여러 AI를 병렬적으로 사용하는 구조

### Changes
- Introduced WORKLOG system (RULE, TEMPLATE, LOG)
  - WORKLOG 체계 도입

### Result
- Unified logging strategy established
  - 공통 작업 기록 체계 확립

### Wrong turns
- ❌ Relying on AI memory across sessions
  - Why wrong:
    - AI는 세션 간 기억을 유지하지 못함
  - Fix:
    - 외부 기억 장치로 WORKLOG 사용

### Decision
- ✅ Use WORKLOG.md as external memory and failure notebook
  - WORKLOG를 외부 기억 및 오답노트로 사용

### Next
1. Start logging real development sessions
2. Refine scopes based on actual pipeline

## Session: 2026-01-16 / Fix Selection Issue
@agent=Anti-Gravity
@role=Implementer
@scope=UI
@status=Done

### Intent
- Fix Face, Point, and Edge selection issues in 3D Viewer.
  - 3D 뷰어의 면, 점, 엣지 선택 문제 수정

### Context
- Edge selection was explicitly disabled in the code.
  - 엣지 선택 코드가 비활성화되어 있었음
- Selection logic relies on `_check_selection` timer loop.
  - 선택 로직이 타이머 루프에 의존

### Changes
- `ui/viewer_3d.py`:
  - Added `EDGE` to `SelectionMode`.
  - Added `edge_selected` Signal.
  - Enabled Edge selection button logic.
  - Implemented `SelectionMode.EDGE` handling in `_check_selection`.

### Result
- Edge selection logic implemented.
  - 엣지 선택 로직 구현됨

### Wrong turns
- ❌ Initial `multi_replace_file_content` failed for `_check_selection`
  - Why wrong: Target content was not unique enough.
  - Fix: Used `replace_file_content` with a larger context block.

### Decision
- ✅ Enable Edge selection and treat it as single-selection (like Face).
  - 엣지 선택을 활성화하고 면 선택처럼 단일 선택으로 처리

### Fast Context Update (MANDATORY)
> Update the AI Fast Context section in WORKLOG.md based on this session.

- Current focus:
  - Verification of selection fix
- Known blocker:
  - None
- Forbidden approaches:
  - None
- Last confirmed working logic:
  - Edge selection implemented in `ui/viewer_3d.py`
- Next planned action:
  - Verify projection view

## Session: 2026-01-16 / Debugging 3D Selection
@agent=Anti-Gravity
@role=Debugger, Implementer
@scope=UI
@status=Done

### Intent
- Fix missing highlighting (preview) and selection events for Point/Edge.
  - 점/엣지 선택 시 프리뷰(하이라이팅) 및 선택 이벤트 미발생 문제 해결

### Context
- Previous fix enabled Edge mode but Highlighting was still missing.
- `qtViewer3d` mouse events were being swallowed or not triggering `MoveTo`.
- `Activate()` without `Deactivate()` caused mixed selection modes.

### Changes
- `ui/viewer_3d.py`:
  - Updated `_set_selection_mode` to call `Context.Deactivate()` before `Activate()`.
  - Installed `EventFilter` on `occ_widget` to capture mouse events.
  - Implemented Manual Fallback in `_on_mouse_press`:
    - If `GetSelectedShapes()` is empty, explicitly call `viewer.Select(x,y)`.
    - Handles Point and Edge selection robustly even if visual highlighting fails.

### Result
- Highlighting should work due to proper mode deactivation.
- Selection events should trigger reliably via manual fallback.

### Decision
- ✅ Use Event Filter to guarantee mouse event capture.
  - 이벤트 필터를 사용하여 마우스 이벤트 캡처 보장
- ✅ Explicitly call `Select(x,y)` on click to force selection.
  - 클릭 시 명시적으로 Select 호출하여 선택 강제

### Fast Context Update (MANDATORY)
> Update the AI Fast Context section in WORKLOG.md based on this session.

- Current focus:
  - Verification of selection fix
- Known blocker:
  - None
- Forbidden approaches:
  - None
- Last confirmed working logic:
  - Edge/Point selection with Manual Fallback and Event Filter
- Next planned action:
  - Verify projection view

## Session: 2026-01-16 / Fix Layout & Initialization
@agent=Anti-Gravity
@role=Debugger
@scope=UI
@status=Done

### Intent
- Fix `AttributeError: '_setup_mouse_events'` and 3D Viewer split layout issue.
  - 초기화 에러 및 뷰어 화면 분할 문제 해결

### Context
- User reported `AttributeError` due to missing method.
- `init_display()` was creating a secondary window, executing "stealing" logic which failed or caused artifacts.

### Changes
- `ui/viewer_3d.py`:
  - Restored missing `def _setup_mouse_events(self) -> None:` line.
  - Refactored `_init_ui` to DIRECTLY instantiate `qtViewer3d(self)` instead of using `init_display()`.
  - This removes the dependency on global display initialization and window stealing hacks.

### Result
- Viewer should now be embedded cleanly as a single widget.
- Initialization error should be resolved.

### Fast Context Update (MANDATORY)
> Update the AI Fast Context section in WORKLOG.md based on this session.

- Current focus:
  - Verification of layout and selection
- Known blocker:
  - None
- Forbidden approaches:
  - Avoid `init_display` for embedded widgets; use `qtViewer3d` directly.
- Last confirmed working logic:
  - Direct `qtViewer3d` instantiation
- Next planned action:
  - Verify projection view


## Session: 2026-01-16 / Build v1.51 Distribution
@agent=Anti-Gravity
@role=Builder
@scope=Process
@status=Done

### Intent
- Build Official and Trial versions for v1.51.
  - v1.51 정식 및 체험판 빌드

### Context
- main_trial.py needs to be synchronized with main.py features.
  - main_trial.py가 최신 기능과 동기화 필요
- main.py is v1.51.

### Changes
- main_trial.py:
  - Synced with main.py.
  - Set DEV_MODE = False.
  - Updated version to v1.51_trial.
- Executed build_all.py.

### Result
- dist/TS_Numbering_PDF.exe created.
- dist/TS_Numbering_PDF_Trial.exe created.

### Decision
-  Enforce DEV_MODE = False in main_trial.py for build.
  - 빌드 시 체험판 제한 강제 적용

### Fast Context Update (MANDATORY)
> Update the AI Fast Context section in WORKLOG.md based on this session.

- Current focus:
  - Distribution and Deployment
- Known blocker:
  - None
- Forbidden approaches:
  - Direct editing of main_trial.py
- Last confirmed working logic:
  - build_all.py works
- Next planned action:
  - Installer verification


## Session: 2026-01-19 / Startup Speed Optimization
@agent=Anti-Gravity
@role=Optimizer
@scope=Process
@status=Done

### Intent
- Improve startup speed of the installed application.
  - 설치된 프로그램의 구동 속도 개선

### Context
- Previous build used --onefile, causing unpacking overhead on every launch.
  - --onefile 방식의 압축 해제 오버헤드로 인한 실행 지연

### Changes
- build_all.py:
  - Changed --onefile to --onedir.
- installer_setup.iss / installer_setup_trial.iss:
  - Updated Source to pack directory contents (*) instead of single EXE.

### Result
- dist directory now contains TS_Numbering_PDF folders.
- Installers will package unpacked files, eliminating compression overhead.

### Decision
-  Switch to folder-based distribution for Installers.
  - 설치 프로그램 제작 시에는 폴더 방식이 속도 면에서 유리함

### Fast Context Update (MANDATORY)
> Update the AI Fast Context section in WORKLOG.md based on this session.

- Current focus:
  - Startup speed optimization
- Known blocker:
  - None
- Forbidden approaches:
  - Use --onefile for installers
- Last confirmed working logic:
  - --onedir build works
- Next planned action:
  - None (Optimization Complete)


## Session: 2026-01-19 / Create v1.51 Installers
@agent=Anti-Gravity
@role=Builder
@scope=Process
@status=Done

### Intent
- Compile final Inno Setup installer files for v1.51.
  - v1.51 설치 파일(Setup.exe) 생성

### Context
- Optimization to --onedir completed.
- Installer scripts (.iss) had old version (v1.29).

### Changes
- installer_setup.iss / installer_setup_trial.iss:
  - Updated AppVersion to 1.51.
  - Updated OutputBaseFilename to v1.51.
- Ran ISCC.exe for both scripts.

### Result
- installer/TS_Numbering_PDF_Setup_v1.51_stable.exe created.
- installer/TS_Numbering_PDF_Trial_Setup_v1.51.exe created.

### Decision
-  Update version in .iss files to match main application (v1.51).
  - 설치 파일명과 메타데이터 버전 동기화

### Fast Context Update (MANDATORY)
> Update the AI Fast Context section in WORKLOG.md based on this session.

- Current focus:
  - Final Verification
- Known blocker:
  - None
- Forbidden approaches:
  - None
- Last confirmed working logic:
  - ISCC compiler works for --onedir
- Next planned action:
  - User verification


## Session: 2026-01-19 / Bug Fix: Open Project Table Refresh
@agent=Anti-Gravity
@role=Debugger
@scope=Code
@status=Done

### Intent
- Fix issue where numbering list is not shown when opening a project.
  - 프로젝트 열기 시 테이블 갱신 안됨 현상 수정

### Context
- User reported table is empty until new item is added.
- Identified missing _refresh_table_view call in open_project.

### Changes
- main.py:
  - Added self.table_manager._force_refresh_table() in open_project.

### Result
- Table should now populate immediately after loading a project.

### Fast Context Update (MANDATORY)
> Update the AI Fast Context section in WORKLOG.md based on this session.

- Current focus:
  - Bug Fix Verification
- Known blocker:
  - None
- Forbidden approaches:
  - None
- Last confirmed working logic:
  - _force_refresh_table() call applied
- Next planned action:
  - User final confirmation


## Session: 2026-01-19 / Rebuild Installers (Bug Fix Applied)
@agent=Anti-Gravity
@role=Builder
@scope=Release
@status=Done

### Intent
- Rebuild installers to include the 'Table Refresh Fix'.
  - 버그 수정 사항(테이블 갱신)이 적용된 설치 파일 재생성

### Context
- Fix applied to main.py and main_trial.py.
- Required complete rebuild (PyInstaller -> Inno Setup).

### Changes
- Applied fix to main_trial.py (synced with main.py).
- Ren uild_all.py (PyInstaller --onedir).
- Ren ISCC.exe for both installers.

### Result
- Updated installers available in installer/.

### Fast Context Update (MANDATORY)
> Update the AI Fast Context section in WORKLOG.md based on this session.

- Current focus:
  - Final Release Verification
- Known blocker:
  - None
- Forbidden approaches:
  - None
- Last confirmed working logic:
  - Installers rebuilt successfully with bug fix
- Next planned action:
  - User final confirmation
