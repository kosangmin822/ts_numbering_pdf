# -*- coding: utf-8 -*-
"""
StampManager - 스탬프 관리 전담 클래스
스탬프 테이블, 스탬프 하이라이트, 스탬프 삭제 등 스탬프 관련 기능을 담당합니다.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from PySide6 import QtCore, QtGui, QtWidgets
import pandas as pd


class StampManager:
    """스탬프 관리 전담 클래스"""

    def __init__(self, main_window):
        """
        StampManager 초기화

        Args:
            main_window: 메인 윈도우 인스턴스 (의존성 주입)
        """
        self.main_window = main_window

    def delete_selected_stamps(self):
        """스탬프 테이블에서 선택된 스탬프들을 삭제합니다."""
        selected_rows = sorted(
            set(index.row() for index in self.main_window.stamp_table.selectedIndexes()),
            reverse=True
        )

        if not selected_rows:
            return

        # 선택된 행들을 역순으로 삭제 (인덱스가 변경되지 않도록)
        for row in selected_rows:
            self.main_window.stamp_table.removeRow(row)

        # 스탬프 테이블 업데이트
        self.main_window._refresh_stamp_table()

        # 하이라이트 초기화
        self.main_window._clear_stamp_highlight()

        # 더티 플래그 설정
        self.main_window._set_dirty()

    def highlight_stamp_from_table(self, row, column):
        """테이블에서 스탬프를 하이라이트합니다."""
        if row < 0 or row >= self.main_window.stamp_table.rowCount():
            return

        # 스탬프 아이템 가져오기
        stamp_key = self.main_window.stamp_table.item(row, 0).text()
        stamp_item = self.main_window.stamps.get(stamp_key)

        if stamp_item:
            self.highlight_stamp(stamp_item)

    def highlight_stamp(self, stamp_item):
        """스탬프를 하이라이트합니다."""
        if not stamp_item:
            return

        # 기존 하이라이트 제거
        self.clear_stamp_highlight()

        # 새로운 스탬프 하이라이트
        self.main_window.current_highlighted_stamp = stamp_item
        self.main_window._draw_stamp(stamp_item)

        # 뷰 업데이트
        self.main_window.view.update()

    def clear_stamp_highlight(self):
        """스탬프 하이라이트를 제거합니다."""
        self.main_window.current_highlighted_stamp = None
        self.main_window.view.update()

    def draw_stamp(self, stamp_item):
        """스탬프를 그립니다."""
        if not stamp_item or not hasattr(self.main_window, 'view'):
            return

        # 스탬프 그리기 로직
        painter = QtGui.QPainter(self.main_window.view)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # 스탬프 위치 계산
        x = int(stamp_item.x * self.main_window.view.width())
        y = int(stamp_item.y * self.main_window.view.height())

        # 스탬프 그리기
        painter.setPen(QtGui.QPen(QtCore.Qt.red, 2))
        painter.drawEllipse(x - 10, y - 10, 20, 20)

        painter.end()

    def refresh_stamp_table(self):
        """스탬프 테이블을 새로고침합니다."""
        if not hasattr(self.main_window, 'stamp_table'):
            return

        # 테이블 초기화
        self.main_window.stamp_table.setRowCount(0)

        # 스탬프 데이터 추가
        for stamp_key, stamp_item in self.main_window.stamps.items():
            row = self.main_window.stamp_table.rowCount()
            self.main_window.stamp_table.insertRow(row)

            # 스탬프 키
            key_item = QtWidgets.QTableWidgetItem(stamp_key)
            self.main_window.stamp_table.setItem(row, 0, key_item)

            # 스탬프 위치
            pos_item = QtWidgets.QTableWidgetItem(f"({stamp_item.x:.3f}, {stamp_item.y:.3f})")
            self.main_window.stamp_table.setItem(row, 1, pos_item)

            # 스탬프 크기
            size_item = QtWidgets.QTableWidgetItem(f"{stamp_item.width:.3f}")
            self.main_window.stamp_table.setItem(row, 2, size_item)

    def update_stamp_selector(self):
        """스탬프 선택기를 업데이트합니다."""
        if not hasattr(self.main_window, 'stamp_selector'):
            return

        # 스탬프 선택기 콤보박스 업데이트
        self.main_window.stamp_selector.clear()

        for stamp_key in self.main_window.stamps.keys():
            self.main_window.stamp_selector.addItem(stamp_key)

    def get_current_stamp_key(self) -> Optional[str]:
        """현재 인덱스에 해당하는 스탬프의 키(이름)를 반환합니다."""
        if not self.main_window.registered_stamps:
            return None
        stamp_keys = list(self.main_window.registered_stamps.keys())
        if 0 <= self.main_window.current_stamp_index < len(stamp_keys):
            return stamp_keys[self.main_window.current_stamp_index]
        return None

    def update_stamp_button_icon(self):
        """현재 선택된 스탬프 이미지로 툴바 버튼의 아이콘을 업데이트합니다."""
        from utils.helpers import icon_if

        if not hasattr(self.main_window, "stamp_button"):
            return
        stamp_key = self.get_current_stamp_key()
        if stamp_key:
            stamp_info = self.main_window.registered_stamps.get(stamp_key)
            if stamp_info and isinstance(stamp_info, dict):
                stamp_path = stamp_info.get("path")
                pixmap = QtGui.QPixmap(stamp_path)
                if not pixmap.isNull():
                    icon = QtGui.QIcon(
                        pixmap.scaled(
                            32, 32, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
                        )
                    )
                    self.main_window.stamp_button.setIcon(icon)
                    self.main_window.stamp_button.setToolTip(f"현재 스탬프: {stamp_key}\n(클릭하여 변경)")
                    return
        # 스탬프가 없거나 잘못된 경우 기본 아이콘으로 설정
        self.main_window.stamp_button.setIcon(icon_if("resources/icons/stamp_off.png"))
        self.main_window.stamp_button.setToolTip("등록된 스탬프 없음")

    def cycle_next_stamp(self):
        """다음 스탬프로 순환시킵니다."""
        if not self.main_window.registered_stamps:
            return
        num_stamps = len(self.main_window.registered_stamps)
        self.main_window.current_stamp_index = (self.main_window.current_stamp_index + 1) % num_stamps
        self.update_stamp_button_icon()

    def select_stamp_by_key(self, stamp_key: str):
        """키로 스탬프를 선택합니다."""
        if not hasattr(self.main_window, 'stamp_selector'):
            return

        index = self.main_window.stamp_selector.findText(stamp_key)
        if index >= 0:
            self.main_window.stamp_selector.setCurrentIndex(index)
            self.update_stamp_button_icon()

    def show_stamp_context_menu(self, pos):
        """스탬프 컨텍스트 메뉴를 표시합니다."""
        if not hasattr(self.main_window, 'stamp_table'):
            return

        # 선택된 항목이 있는지 확인
        selected_items = self.main_window.stamp_table.selectedItems()
        if not selected_items:
            return

        # 컨텍스트 메뉴 생성
        menu = QtWidgets.QMenu(self.main_window.stamp_table)

        # 삭제 액션
        delete_action = menu.addAction("삭제")
        delete_action.triggered.connect(self.delete_selected_stamps)

        # 메뉴 표시
        menu.exec_(self.main_window.stamp_table.mapToGlobal(pos))

    def build_stamps_dataframe(self):
        """스탬프 데이터를 DataFrame으로 변환합니다."""
        data = []
        for stamp_key, stamp_item in self.main_window.stamps.items():
            data.append({
                'key': stamp_key,
                'x': stamp_item.x,
                'y': stamp_item.y,
                'width': stamp_item.width,
                'height': stamp_item.height
            })

        return pd.DataFrame(data)
