# Main.py 리팩토링 계획 (Ver 2)

## 📊 현재 상태 분석

### 기본 정보
- **현재 라인 수**: 5,182줄
- **목표 라인 수**: 1,500줄 이하
- **줄여야 할 라인**: 약 3,682줄 (71% 감소)
- **클래스 수**: 2개 (Worker, PdfAnnotator)
- **메서드 수**: 170개 (PdfAnnotator 클래스)

## 🎯 리팩토링 전략

### 목표
1. Main.py를 1,500줄 이하로 축소
2. 기능별로 모듈화하여 유지보수성 향상
3. 각 단계마다 실행 가능한 상태 유지 (테스트 가능)
4. Git 커밋으로 각 단계 백업

### 핵심 원칙
- **한 번에 하나씩**: 한 매니저씩 분리
- **테스트 우선**: 매 단계 실행 확인
- **점진적 개선**: 작은 단위로 커밋
- **백업 철저**: 각 단계마다 커밋

## 📦 분리할 Manager 클래스

### 1단계: 3D Viewer Manager (우선순위: 높음)
**예상 라인 수**: ~600줄
**이유**: 3D 뷰어는 독립적이며 코드가 많음

**분리 대상 메서드**:
- `open_3d_model()`
- `on_3d_load_finished()`
- `on_3d_load_error()`
- `set_viewport()`
- `apply_viewport_from_data()`
- `update_view_info()`
- `update_custom_view()`
- `apply_custom_view()`
- `on_distance_slider_changed()`
- `set_view_mode()`
- `change_background_color()`
- `reset_colors()`
- `change_transparency()`
- `reset_3d_colors()`
- `_setup_3d_viewer_color_controls()`
- `_create_color_palette()`
- `_select_color_from_palette()`
- `_position_integrated_control_panel()`
- `_position_color_control_panel()`
- `_clear_3d_viewer()`
- `toggle_3d_navigator()`

**파일 생성**: `managers/viewer_3d_manager.py`

---

### 2단계: Table Manager (우선순위: 높음)
**예상 라인 수**: ~400줄
**이유**: 테이블 관련 기능이 복잡하고 많음

**분리 대상 메서드**:
- `_append_table_row()`
- `_format_3d_parameter()`
- `on_table_cell_clicked()`
- `on_table_selection_changed()`
- `on_table_item_changed()`
- `_highlight_from_row()`
- `_highlight_by_no()`
- `_refresh_table_view()`
- `_sync_items_from_table()`
- `_force_refresh_table()`
- `show_table_context_menu()`
- `save_viewport_parameters()`
- `copy_format()`
- `paste_format()`
- `_reset_all_tables()`

**파일 생성**: `managers/table_manager.py`

---

### 3단계: UI Manager (우선순위: 높음)
**예상 라인 수**: ~500줄
**이유**: 메뉴, 툴바, 단축키 설정이 많음

**분리 대상 메서드**:
- `_create_menus()`
- `_create_toolbar()`
- `_create_shortcuts()`
- `_create_toolbar_group()`
- `_add_toolbar_action()`
- `_update_line_style_button_icon()`
- `_update_arrow_style_button_icon()`
- `_update_preview_button_visuals()`
- `_update_stamp_button_icon()`
- `_sync_ui_to_current_mode()`
- `_update_undo_redo_hint()`
- `_update_status()`

**파일 생성**: `managers/ui_manager.py`

---

### 4단계: Stamp Manager (우선순위: 중간)
**예상 라인 수**: ~300줄
**이유**: 스탬프 기능이 독립적

**분리 대상 메서드**:
- `open_stamp_settings()`
- `open_stamp_manager()`
- `_update_stamp_selector()`
- `_refresh_stamp_table()`
- `_draw_stamp()`
- `_highlight_stamp()`
- `_highlight_stamp_from_table()`
- `_clear_stamp_highlight()`
- `_delete_selected_stamps()`
- `_get_current_stamp_key()`
- `_select_stamp_by_key()`
- `_cycle_next_stamp()`
- `_show_stamp_context_menu()`
- `toggle_stamps_view()`

**파일 생성**: `managers/stamp_manager.py`

---

### 5단계: PDF Manager (우선순위: 중간)
**예상 라인 수**: ~400줄
**이유**: PDF 로드, 저장, 페이지 관리 기능

**분리 대상 메서드**:
- `import_pdf()`
- `import_pdf_from_path()`
- `load_page()`
- `go_prev()`
- `go_next()`
- `_go_to_page_from_spinbox()`
- `_update_page_navigation_ui()`
- `_populate_thumbnails()`
- `_update_thumbnail_selection()`
- `_clear_thumbnails()`
- `rotate_page_left()`
- `rotate_page_right()`
- `_append_pdf()`
- `_render_factor_for_scale()`
- `_maybe_rerender_for_zoom()`
- `rerender_now()`
- `fit_to_window()`
- `set_auto_highres()`

**파일 생성**: `managers/pdf_manager.py`

---

### 6단계: Project Manager (우선순위: 중간)
**예상 라인 수**: ~300줄
**이유**: 프로젝트 파일 관리 기능

**분리 대상 메서드**:
- `new_project()`
- `open_project_dialog()`
- `open_project()`
- `save_project()`
- `save_project_as()`
- `_write_tsn()`
- `publish_project()`
- `_close_current_doc()`
- `_reset_state_for_new()`
- `_set_dirty()`
- `_update_window_title()`
- `_maybe_save()`

**파일 생성**: `managers/project_manager.py`

---

### 7단계: Drawing Manager (우선순위: 낮음)
**예상 라인 수**: ~350줄
**이유**: 그리기/렌더링 기능

**분리 대상 메서드**:
- `_draw_label()`
- `_draw_flow_elements()`
- `_update_flow_view()`
- `_create_preview_items()`
- `_move_preview_items()`
- `_refresh_preview_text()`
- `highlight_label()`
- `clear_highlight()`
- `clear_selection_and_highlight()`
- `_apply_highlight_from_table()`
- `_sync_highlight_from_table()`
- `_reapply_highlight_from_selection()`
- `_ellipse_brush()`

**파일 생성**: `managers/drawing_manager.py`

---

### 8단계: Item Manager (우선순위: 낮음)
**예상 라인 수**: ~250줄
**이유**: 아이템 삽입, 삭제, 수정 기능

**분리 대상 메서드**:
- `on_clicked()`
- `execute_item_insertion()`
- `cancel_insert_mode()`
- `insert_excel_style()`
- `insert_precision_style()`
- `delete_items()`
- `undo()`
- `redo()`
- `renumber_items_by_unit()`
- `set_start_number()`
- `_get_precision_no()`

**파일 생성**: `managers/item_manager.py`

---

### 9단계: Export Manager (우선순위: 낮음)
**예상 라인 수**: ~200줄
**이유**: 내보내기 기능

**분리 대상 메서드**:
- `_cmd_export_pdf()`
- `_save_pdf_with_labels()`
- `export_csv_dialog()`
- `export_xlsx_dialog()`
- `_export_csv()`
- `_export_xlsx()`
- `_export_current_page_jpg_with_labels()`
- `_build_items_dataframe()`
- `_build_stamps_dataframe()`

**파일 생성**: `managers/export_manager.py`

---

### 10단계: Style Manager (우선순위: 낮음)
**예상 라인 수**: ~150줄
**이유**: 스타일 설정 기능

**분리 대상 메서드**:
- `open_numbering_settings()`
- `_open_numbering_settings_dialog()`
- `set_individual_style()`
- `adjust_label_style()`
- `_cycle_line_style()`
- `_cycle_arrow_style()`
- `_toggle_show_start_end()`

**파일 생성**: `managers/style_manager.py`

---

## 📅 작업 순서 (총 10단계)

### Phase 1: 핵심 기능 분리 (3단계)
1. ✅ **3D Viewer Manager** (600줄 감소)
2. ✅ **Table Manager** (400줄 감소)
3. ✅ **UI Manager** (500줄 감소)
   - 예상 감소: **1,500줄**

### Phase 2: 중요 기능 분리 (3단계)
4. ✅ **Stamp Manager** (300줄 감소)
5. ✅ **PDF Manager** (400줄 감소)
6. ✅ **Project Manager** (300줄 감소)
   - 예상 감소: **1,000줄**

### Phase 3: 보조 기능 분리 (4단계)
7. ✅ **Drawing Manager** (350줄 감소)
8. ✅ **Item Manager** (250줄 감소)
9. ✅ **Export Manager** (200줄 감소)
10. ✅ **Style Manager** (150줄 감소)
    - 예상 감소: **950줄**

**총 예상 감소**: 3,450줄
**최종 예상 라인 수**: ~1,730줄 (목표 달성 ✅)

---

## 🔧 각 단계 작업 프로세스

### 표준 작업 순서
1. **분석**: 해당 매니저의 메서드 목록 확인
2. **생성**: 새 매니저 파일 생성
3. **이동**: 메서드를 매니저로 이동
4. **연결**: Main.py에서 매니저 초기화 및 연결
5. **테스트**: 프로그램 실행 확인
6. **커밋**: Git 커밋으로 백업
7. **반복**: 다음 단계로

### 테스트 체크리스트
- [ ] 프로그램 실행 성공
- [ ] PDF 로드 정상 작동
- [ ] 넘버링 추가/삭제 정상 작동
- [ ] 3D 뷰어 정상 작동
- [ ] 테이블 정상 작동
- [ ] 프로젝트 저장/불러오기 정상 작동

---

## 🚀 시작 준비

현재 위치: **Phase 1, Step 1 - 3D Viewer Manager 분리 준비**

다음 액션:
1. `managers/viewer_3d_manager.py` 파일 생성
2. 3D Viewer 관련 메서드 식별 및 이동
3. Main.py에 Viewer3DManager 통합
4. 테스트 및 커밋

---

작업 시작일: 2025-10-17
목표 완료일: 2025-10-17 (같은 날 완료 목표)

