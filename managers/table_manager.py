# -*- coding: utf-8 -*-
"""
TableManager - 테이블 관리 전담 클래스
넘버링 리스트 테이블의 모든 기능을 담당합니다.
"""
from __future__ import annotations
import json
from typing import List, Optional
from PySide6 import QtCore, QtGui, QtWidgets

from core.models import MarkItem
from utils.helpers import dim_format, normalize_signed_text, strip_prefix_for_value, to_float_or_none


class TableManager:
    """넘버링 리스트 테이블 관리 전담 클래스"""

    def __init__(self, main_window):
        """
        TableManager 초기화

        Args:
            main_window: 메인 윈도우 인스턴스 (의존성 주입)
        """
        self.main_window = main_window
        self.table = None
        self.highlight_enabled = True

    def set_table(self, table: QtWidgets.QTableWidget):
        """
        테이블 위젯을 설정합니다.

        Args:
            table: QTableWidget 인스턴스
        """
        self.table = table
        self._setup_table_connections()

    def _setup_table_connections(self):
        """테이블 이벤트 연결을 설정합니다."""
        if not self.table:
            return

        self.table.itemChanged.connect(self.on_table_item_changed)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        self.table.itemSelectionChanged.connect(self._sync_highlight_from_table)
        self.table.currentCellChanged.connect(lambda *_: self._sync_highlight_from_table())
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)

    def _append_table_row(self, it: MarkItem):
        """
        테이블에 새로운 행을 추가합니다.

        Args:
            it: MarkItem 인스턴스
        """
        if not self.table:
            return

        r = self.table.rowCount()
        self.table.insertRow(r)
        no_val = it.no
        if abs(no_val - round(no_val)) < 1e-9:
            no_str = f"{no_val:.0f}"
        else:
            no_str = f"{no_val:g}"

        # No 컬럼 (중앙 정렬)
        no_item = QtWidgets.QTableWidgetItem()
        no_item.setTextAlignment(QtCore.Qt.AlignCenter)
        no_item.setData(QtCore.Qt.DisplayRole, no_str)
        no_item.setFlags(no_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.table.setItem(r, 0, no_item)

        # Type 컬럼 (중앙 정렬)
        type_item = QtWidgets.QTableWidgetItem(it.dim_type)
        type_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.table.setItem(r, 1, type_item)

        # Dim 컬럼 (중앙 정렬)
        dim_item = QtWidgets.QTableWidgetItem(dim_format(it.dim_type, it.value))
        dim_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.table.setItem(r, 2, dim_item)

        # Max 컬럼 (중앙 정렬)
        max_item = QtWidgets.QTableWidgetItem(normalize_signed_text(it.tol_plus))
        max_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.table.setItem(r, 3, max_item)

        # Min 컬럼 (중앙 정렬)
        min_item = QtWidgets.QTableWidgetItem(normalize_signed_text(it.tol_minus))
        min_item.setTextAlignment(QtCore.Qt.AlignCenter)
        self.table.setItem(r, 4, min_item)

        # 3D Parameter 컬럼 (중앙 정렬, 새로운 포맷 적용, 읽기 전용)
        viewport_display = self._format_3d_parameter(it.viewport_parameters)
        viewport_item = QtWidgets.QTableWidgetItem(viewport_display)
        viewport_item.setTextAlignment(QtCore.Qt.AlignCenter)
        viewport_item.setFlags(viewport_item.flags() & ~QtCore.Qt.ItemIsEditable)  # 읽기 전용 설정
        self.table.setItem(r, 10, viewport_item)

        # x1~x5 컬럼
        x_values = list(getattr(it, "x_values", ["", "", "", "", ""]))
        if len(x_values) < 5:
            x_values += [""] * (5 - len(x_values))
        elif len(x_values) > 5:
            x_values = x_values[:5]
        for idx, value in enumerate(x_values):
            col = 5 + idx
            extra_item = QtWidgets.QTableWidgetItem(str(value))
            extra_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table.setItem(r, col, extra_item)
            self._apply_x_value_color(r, col, it)

    def _format_3d_parameter(self, viewport_parameters: str) -> str:
        """
        3D 뷰포트 파라메터를 (x, y, z, distance) 형태로 포맷팅합니다.

        Args:
            viewport_parameters (str): JSON 형태의 뷰포트 파라메터 문자열
        Returns:
            str: 포맷팅된 3D 파라메터 문자열
        """
        if not viewport_parameters or not viewport_parameters.strip():
            return ""

        try:
            data = json.loads(viewport_parameters)
            x = round(data.get("x", 0), 1)
            y = round(data.get("y", 0), 1)
            z = round(data.get("z", 0), 1)
            distance = round(data.get("distance", 0), 1)
            return f"({x}, {y}, {z}, {distance}d)"
        except (json.JSONDecodeError, KeyError, TypeError):
            return viewport_parameters  # 파싱 실패 시 원본 반환

    def _get_dim_bounds(self, target_item: MarkItem):
        base = to_float_or_none(target_item.value)
        if base is None:
            return None
        tol_plus = to_float_or_none(target_item.tol_plus)
        tol_minus = to_float_or_none(target_item.tol_minus)
        if tol_plus is None and tol_minus is None:
            return None
        if tol_plus is None:
            tol_plus = 0.0
        if tol_minus is None:
            tol_minus = 0.0
        min_val = base + tol_minus
        max_val = base + tol_plus
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        return min_val, max_val

    def _apply_x_value_color(self, row: int, col: int, target_item: MarkItem):
        if not self.table:
            return
        item = self.table.item(row, col)
        if not item:
            return
        value = to_float_or_none(item.text())
        bounds = self._get_dim_bounds(target_item)
        if value is None or bounds is None:
            item.setForeground(QtGui.QBrush())
            return
        min_val, max_val = bounds
        if min_val <= value <= max_val:
            item.setForeground(QtGui.QColor("blue"))
        else:
            item.setForeground(QtGui.QColor("red"))

    def _refresh_x_value_colors(self, row: int, target_item: Optional[MarkItem] = None):
        if not self.table:
            return
        if target_item is None:
            target_item = self._get_target_item(row)
        if not target_item:
            return
        for c in range(5, 10):
            self._apply_x_value_color(row, c, target_item)

    def on_table_cell_clicked(self, row: int, col: int):
        """
        테이블 셀 클릭 이벤트 처리

        Args:
            row: 클릭된 행 번호
            col: 클릭된 열 번호
        """
        # 3D 뷰포트 기능: 어떤 컬럼을 클릭해도 해당 행의 뷰포트 적용
        target_item = self._get_target_item(row)

        if target_item and target_item.viewport_parameters and target_item.viewport_parameters.strip():
            try:
                viewport_data = json.loads(target_item.viewport_parameters)
                if hasattr(self.main_window, 'apply_viewport_from_data'):
                    if self.main_window.apply_viewport_from_data(viewport_data):
                        print(f"행 {row}의 저장된 뷰포트가 적용되었습니다.")
                    else:
                        print("뷰포트 적용에 실패했습니다.")
            except json.JSONDecodeError as e:
                print(f"뷰포트 데이터 파싱 오류: {e}")
            except Exception as e:
                print(f"뷰포트 적용 중 오류: {e}")

        # 하이라이트 기능
        if not self.highlight_enabled:
            return
        self._highlight_from_row(row)

    def on_table_selection_changed(self):
        """테이블 선택 변경 이벤트 처리"""
        ranges = self.table.selectedRanges()
        if not ranges:
            return
        self._highlight_from_row(ranges[0].topRow())

    def _highlight_from_row(self, row: int):
        """
        지정된 행을 하이라이트합니다.

        Args:
            row: 하이라이트할 행 번호
        """
        if not self.table or row < 0 or row >= self.table.rowCount():
            return

        try:
            no_item = self.table.item(row, 0)
            if not no_item:
                return

            item_no = float(no_item.data(QtCore.Qt.DisplayRole))
            self._highlight_by_no(item_no)
        except (ValueError, TypeError):
            pass

    def _highlight_by_no(self, no: int):
        """
        지정된 번호의 아이템을 하이라이트합니다.

        Args:
            no: 하이라이트할 아이템 번호
        """
        if hasattr(self.main_window, 'highlight_label'):
            # 메인 윈도우의 items에서 해당 번호의 아이템 찾기
            target_item = None
            # 페이지별 개별 넘버링 모드 확인
            if hasattr(self.main_window, "cb_separate_numbering") and self.main_window.numbering_mode == "page_specific":
                # 현재 페이지의 아이템만 검색
                for item in self.main_window.items:
                    if item.page_index == self.main_window.cur_page_index and abs(item.no - no) < 1e-9:
                        target_item = item
                        break
            else:
                # 전체 아이템에서 검색
                for item in self.main_window.items:
                    if abs(item.no - no) < 1e-9:
                        target_item = item
                        break
            if target_item:
                self.main_window.highlight_label(target_item)

    def on_table_item_changed(self, qitem: QtWidgets.QTableWidgetItem):
        """
        테이블 아이템 변경 이벤트 처리

        Args:
            qitem: 변경된 테이블 아이템
        """
        if not self.table:
            return

        r, c = qitem.row(), qitem.column()
        if r < 0 or c < 0:
            return

        # 아이템 번호 가져오기
        no_item = self.table.item(r, 0)
        if not no_item:
            return

        try:
            item_no = float(no_item.data(QtCore.Qt.DisplayRole))
        except (ValueError, TypeError):
            return

        # 타겟 아이템 찾기
        target_item = self._get_target_item(r)
        if not target_item:
            return

        # 컬럼별 처리
        if c == 1:  # Type 컬럼
            from utils.helpers import strip_prefix_for_value
            from core.models import DIM_TYPES

            txt = qitem.text()
            target_item.dim_type = txt if txt in DIM_TYPES else "선형"
            raw = target_item.value
            self.table.blockSignals(True)
            dm = self.table.item(r, 2)
            if dm:
                dm.setText(dim_format(target_item.dim_type, raw))
            self.table.blockSignals(False)

        elif c == 2:  # Dim 컬럼
            from utils.helpers import strip_prefix_for_value

            raw = strip_prefix_for_value(target_item.dim_type, qitem.text())
            target_item.value = raw
            self.table.blockSignals(True)
            qitem.setText(dim_format(target_item.dim_type, raw))
            self.table.blockSignals(False)
            self._refresh_x_value_colors(r, target_item)

        elif c == 3:  # Max 컬럼
            norm = normalize_signed_text(qitem.text())
            target_item.tol_plus = norm
            self.table.blockSignals(True)
            qitem.setText(norm)
            self.table.blockSignals(False)
            self._refresh_x_value_colors(r, target_item)

        elif c == 4:  # Min 컬럼
            norm = normalize_signed_text(qitem.text())
            target_item.tol_minus = norm
            self.table.blockSignals(True)
            qitem.setText(norm)
            self.table.blockSignals(False)
            self._refresh_x_value_colors(r, target_item)

        elif 5 <= c <= 9:  # x1~x5 컬럼
            if not hasattr(target_item, "x_values") or target_item.x_values is None:
                target_item.x_values = ["", "", "", "", ""]
            if len(target_item.x_values) < 5:
                target_item.x_values = target_item.x_values + [""] * (5 - len(target_item.x_values))
            elif len(target_item.x_values) > 5:
                target_item.x_values = target_item.x_values[:5]
            target_item.x_values[c - 5] = qitem.text()
            qitem.setTextAlignment(QtCore.Qt.AlignCenter)
            self._apply_x_value_color(r, c, target_item)

        elif c == 10:  # 3D Parameter 컬럼 처리
            # 3D Parameter는 읽기 전용이므로 원본 데이터로 되돌림
            self.table.blockSignals(True)
            formatted_value = self._format_3d_parameter(target_item.viewport_parameters)
            qitem.setText(formatted_value)
            qitem.setTextAlignment(QtCore.Qt.AlignCenter)
            qitem.setFlags(qitem.flags() & ~QtCore.Qt.ItemIsEditable)  # 읽기 전용 유지
            self.table.blockSignals(False)

        # 변경사항 저장
        if hasattr(self.main_window, '_set_dirty'):
            self.main_window._set_dirty()

    def _sync_highlight_from_table(self):
        """테이블에서 하이라이트 동기화"""
        QtCore.QTimer.singleShot(0, self._apply_highlight_from_table)

    def _apply_highlight_from_table(self):
        """하이라이트 적용"""
        if not self.highlight_enabled:
            if hasattr(self.main_window, 'clear_highlight'):
                self.main_window.clear_highlight()
            return

        row = self.table.currentRow()
        if row < 0:
            if hasattr(self.main_window, 'clear_highlight'):
                self.main_window.clear_highlight()
            return
        self._highlight_from_row(row)

    def _get_target_item(self, row: int) -> Optional[MarkItem]:
        """
        지정된 행에 해당하는 MarkItem을 가져옵니다.

        Args:
            row: 행 번호
        Returns:
            MarkItem 또는 None
        """
        if not hasattr(self.main_window, 'items'):
            return None

        # 페이지별 개별 넘버링 모드 확인
        if hasattr(self.main_window, "cb_separate_numbering") and self.main_window.numbering_mode == "page_specific":
            items_to_display = [it for it in self.main_window.items if it.page_index == self.main_window.cur_page_index]
        else:
            items_to_display = self.main_window.items

        items_to_display.sort(key=lambda x: x.no)
        if row < len(items_to_display):
            return items_to_display[row]
        return None

    def _force_refresh_table(self):
        """테이블을 강제로 새로고침하여 새로운 포맷을 적용합니다."""
        self._refresh_table_view()

    def _refresh_table_view(self):
        """체크박스 상태에 따라 테이블 뷰를 새로고침합니다."""
        if not self.table:
            return

        self.table.blockSignals(True)
        self.table.setRowCount(0)
        items_to_display = []

        # hasattr를 사용하여 cb_separate_numbering이 생성되었는지 먼저 확인 (안전장치)
        if hasattr(self.main_window, "cb_separate_numbering") and self.main_window.numbering_mode == "page_specific":
            items_to_display = [it for it in self.main_window.items if it.page_index == self.main_window.cur_page_index]
        else:
            items_to_display = self.main_window.items

        items_to_display.sort(key=lambda x: x.no)
        for it in items_to_display:
            self._append_table_row(it)
        self.table.blockSignals(False)

    def _sync_items_from_table(self):
        """테이블의 데이터를 MarkItem으로 동기화합니다."""
        if not self.table:
            return

        self.table.clearFocus()
        QtWidgets.QApplication.processEvents()
        rows = min(self.table.rowCount(), len(self.main_window.items))

        for r in range(rows):
            it = self.main_window.items[r]
            dt_item = self.table.item(r, 1)
            it.dim_type = dt_item.text() if dt_item else it.dim_type
            if it.dim_type not in ["선형", "Ø", "R", "C", "기타"]:
                it.dim_type = "선형"
            dm_item = self.table.item(r, 2)
            it.value = strip_prefix_for_value(it.dim_type, dm_item.text()) if dm_item else it.value
            p_item = self.table.item(r, 3)
            m_item = self.table.item(r, 4)
            it.tol_plus = normalize_signed_text(p_item.text()) if p_item else it.tol_plus
            it.tol_minus = normalize_signed_text(m_item.text()) if m_item else it.tol_minus
            x_values = []
            for c in range(5, 10):
                x_item = self.table.item(r, c)
                x_values.append(x_item.text() if x_item else "")
            it.x_values = x_values
            # 3D 뷰포트 파라메터 동기화 (5번째 컬럼)
            # 테이블에는 포맷팅된 값이 표시되지만, 원본 JSON 데이터는 이미 MarkItem에 저장되어 있음
            # 따라서 별도로 동기화할 필요 없음 (이미 저장된 원본 데이터 유지)

    def show_table_context_menu(self, pos):
        """테이블 컨텍스트 메뉴를 표시합니다."""
        if not self.table:
            return

        menu = QtWidgets.QMenu(self.main_window)
        is_item_selected = len(self.table.selectedIndexes()) > 0

        # --- 삽입 메뉴 ---
        insert_excel_action = menu.addAction("번호 밀기(현재번호  +1)")
        insert_precision_action = menu.addAction("번호 삽입(unit : 0.1)")
        insert_excel_action.setShortcut(QtGui.QKeySequence("Insert"))
        insert_precision_action.setShortcut(QtGui.QKeySequence("Shift+Insert"))

        # --- 삭제 및 재정렬 메뉴 ---
        menu.addSeparator()
        delete_only_action = menu.addAction("해당 넘버링 삭제")
        renumber_action = menu.addAction("넘버링 자연수 재정렬(unit : 1)")
        delete_only_action.setShortcut(QtGui.QKeySequence("Delete"))
        renumber_action.setShortcut(QtGui.QKeySequence("Shift+Delete"))

        # --- 서식 및 기타 메뉴 ---
        menu.addSeparator()
        style_action = menu.addAction("개별 서식 지정/해제...")
        style_action.setShortcut(QtGui.QKeySequence("F2"))

        # 3D 뷰포트 파라메터 저장 메뉴
        menu.addSeparator()
        save_viewport_action = menu.addAction("3d 뷰포트 파라메터 저장")
        save_viewport_action.setEnabled(is_item_selected)

        menu.addSeparator()
        if hasattr(self.main_window, 'a_highlight'):
            menu.addAction(self.main_window.a_highlight)

        # 선택된 항목이 없을 경우 비활성화
        for action in [delete_only_action, renumber_action, style_action]:
            action.setEnabled(is_item_selected)

        # 액션과 함수 연결
        insert_excel_action.triggered.connect(self.main_window.insert_excel_style)
        insert_precision_action.triggered.connect(self.main_window.insert_precision_style)
        delete_only_action.triggered.connect(self.main_window.delete_items)
        renumber_action.triggered.connect(self.main_window.renumber_items_by_unit)
        style_action.triggered.connect(self.main_window.set_individual_style)
        save_viewport_action.triggered.connect(self.main_window.save_viewport_parameters)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def toggle_highlighting(self, checked: bool):
        """하이라이트 기능을 토글합니다."""
        self.highlight_enabled = checked
        if not checked and hasattr(self.main_window, 'clear_highlight'):
            self.main_window.clear_highlight()

    def clear_highlight(self):
        """하이라이트를 지웁니다."""
        if hasattr(self.main_window, 'clear_highlight'):
            self.main_window.clear_highlight()

    def clear_selection_and_highlight(self):
        """선택과 하이라이트를 모두 지웁니다."""
        if self.table:
            self.table.clearSelection()
        self.clear_highlight()

    def _reapply_highlight_from_selection(self, same_page_only=False):
        """선택에서 하이라이트를 다시 적용합니다."""
        if not self.table:
            return

        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        # 첫 번째 선택된 아이템의 행을 사용
        row = selected_items[0].row()
        self._highlight_from_row(row)
