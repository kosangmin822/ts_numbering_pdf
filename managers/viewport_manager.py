# -*- coding: utf-8 -*-
"""
ViewportManager - 3D 뷰포트 관리 전담 클래스
3D 뷰어의 모든 기능을 담당합니다.
"""
from __future__ import annotations
import json
import numpy as np
from typing import Optional, Dict, Any
from PySide6 import QtCore, QtGui, QtWidgets


class ViewportManager:
    """3D 뷰포트 관리 전담 클래스"""

    def __init__(self, main_window):
        """
        ViewportManager 초기화

        Args:
            main_window: 메인 윈도우 인스턴스 (의존성 주입)
        """
        self.main_window = main_window
        self.plotter = None
        self.current_view_mode = "shading"
        self.current_transparency = 0

    def set_plotter(self, plotter):
        """
        3D 플로터를 설정합니다.

        Args:
            plotter: 3D 플로터 인스턴스
        """
        self.plotter = plotter

    def save_viewport_parameters(self):
        """
        현재 3D 뷰포트 파라메터를 선택된 테이블 항목에 저장합니다.
        """
        if not self.plotter:
            QtWidgets.QMessageBox.warning(
                self.main_window, "알림", "3D 모델을 먼저 불러와야 합니다."
            )
            return

        # 현재 뷰 정보 가져오기
        try:
            position = np.array(self.plotter.camera.position)
            focal_point = np.array(self.plotter.camera.focal_point)
            view_direction = focal_point - position
            distance = np.linalg.norm(view_direction)
            if distance > 0:
                view_direction = view_direction / distance

            # 뷰포트 정보를 JSON 형식으로 포맷팅
            viewport_data = {
                "x": round(view_direction[0], 2),
                "y": round(view_direction[1], 2),
                "z": round(view_direction[2], 2),
                "distance": round(distance, 2),
            }
            viewport_info = json.dumps(viewport_data, ensure_ascii=False)

            # 선택된 행들에 뷰포트 정보 저장
            selected_rows = set()
            for index in self.main_window.table.selectedIndexes():
                selected_rows.add(index.row())

            for row in selected_rows:
                # 먼저 원본 데이터를 MarkItem에 저장
                target_item = self._get_target_item(row)
                if target_item:
                    target_item.viewport_parameters = viewport_info

                # 테이블에 포맷팅된 값으로 표시
                if hasattr(self.main_window, 'table_manager'):
                    formatted_display = self.main_window.table_manager._format_3d_parameter(viewport_info)
                    item = QtWidgets.QTableWidgetItem(formatted_display)
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                    self.main_window.table.setItem(row, 5, item)

            if hasattr(self.main_window, '_set_dirty'):
                self.main_window._set_dirty()

            QtWidgets.QMessageBox.information(
                self.main_window, "완료",
                f"{len(selected_rows)}개 항목에 3D 뷰포트 파라메터가 저장되었습니다."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.main_window, "오류",
                f"뷰포트 파라메터 저장 중 오류가 발생했습니다:\n{e}"
            )

    def apply_viewport_from_data(self, viewport_data: Dict[str, Any]) -> bool:
        """
        JSON 형식의 뷰포트 데이터를 받아서 3D 뷰어에 적용합니다.

        Args:
            viewport_data (dict): {"x": float, "y": float, "z": float, "distance": float}
        Returns:
            bool: 적용 성공 여부
        """
        if not self.plotter:
            return False

        try:
            x = viewport_data.get("x", 0)
            y = viewport_data.get("y", 0)
            z = viewport_data.get("z", 0)
            distance = viewport_data.get("distance", 1.0)

            # 뷰 방향 벡터 계산
            view_direction = np.array([x, y, z])
            view_direction = view_direction / np.linalg.norm(view_direction)

            # 카메라 위치 설정
            focal_point = np.array(self.plotter.camera.focal_point)
            position = focal_point - view_direction * distance

            self.plotter.camera.position = position
            self.plotter.camera.focal_point = focal_point
            self.plotter.camera.up = [0, 1, 0]  # 기본 up 벡터

            # 뷰 업데이트
            self.plotter.render()
            return True

        except Exception as e:
            print(f"뷰포트 적용 오류: {e}")
            return False

    def update_view_info(self):
        """현재 뷰 정보를 업데이트합니다."""
        if not self.plotter:
            if hasattr(self.main_window, 'view_info_label'):
                self.main_window.view_info_label.setText("3D 모델을 불러오세요")
            return

        try:
            position = np.array(self.plotter.camera.position)
            focal_point = np.array(self.plotter.camera.focal_point)
            view_direction = focal_point - position
            distance = np.linalg.norm(view_direction)

            if distance > 0:
                view_direction = view_direction / distance

            # 뷰 정보를 UI에 표시
            if hasattr(self.main_window, 'view_info_label'):
                info_text = f"""X: {view_direction[0]:.2f}  Y: {view_direction[1]:.2f}  Z: {view_direction[2]:.2f}
거리: {distance:.2f}"""
                self.main_window.view_info_label.setText(info_text)

        except Exception as e:
            print(f"뷰 정보 업데이트 오류: {e}")

    def set_viewport(self, view_name: str):
        """
        미리 정의된 뷰포트로 전환합니다.

        Args:
            view_name: 뷰포트 이름 (한국어 또는 영어)
        """
        if not self.plotter:
            return

        # 한국어 이름을 영어로 매핑
        korean_to_english = {
            "상면": "top",
            "하면": "bottom",
            "정면": "front",
            "후면": "back",
            "좌측면": "left",
            "우측면": "right",
        }

        # 한국어 이름이면 영어로 변환
        if view_name in korean_to_english:
            view_name = korean_to_english[view_name]

        viewport_configs = {
            "front": {"x": 0, "y": 0, "z": 1, "distance": 1.0},
            "back": {"x": 0, "y": 0, "z": -1, "distance": 1.0},
            "left": {"x": -1, "y": 0, "z": 0, "distance": 1.0},
            "right": {"x": 1, "y": 0, "z": 0, "distance": 1.0},
            "top": {"x": 0, "y": 1, "z": 0, "distance": 1.0},
            "bottom": {"x": 0, "y": -1, "z": 0, "distance": 1.0},
            "isometric": {"x": 0.5, "y": 0.5, "z": 0.5, "distance": 1.0},
        }

        if view_name in viewport_configs:
            self.apply_viewport_from_data(viewport_configs[view_name])
            print(f"뷰포트 전환: {view_name}")

    def update_custom_view(self):
        """사용자 정의 뷰를 업데이트합니다."""
        if not self.plotter:
            return

        try:
            # 현재 뷰 정보를 사용자 정의 컨트롤에 반영
            position = np.array(self.plotter.camera.position)
            focal_point = np.array(self.plotter.camera.focal_point)
            view_direction = focal_point - position
            distance = np.linalg.norm(view_direction)

            if distance > 0:
                view_direction = view_direction / distance

            if hasattr(self.main_window, 'custom_x_spin'):
                # 이벤트 연결을 일시적으로 해제하여 무한 루프 방지
                self.main_window.custom_x_spin.blockSignals(True)
                self.main_window.custom_y_spin.blockSignals(True)
                self.main_window.custom_z_spin.blockSignals(True)

                self.main_window.custom_x_spin.setValue(view_direction[0])
                self.main_window.custom_y_spin.setValue(view_direction[1])
                self.main_window.custom_z_spin.setValue(view_direction[2])
                self.main_window.distance_slider.setValue(int(distance * 100))

                # 이벤트 연결 복원
                self.main_window.custom_x_spin.blockSignals(False)
                self.main_window.custom_y_spin.blockSignals(False)
                self.main_window.custom_z_spin.blockSignals(False)

        except Exception as e:
            print(f"사용자 정의 뷰 업데이트 오류: {e}")

    def on_custom_view_changed(self):
        """사용자 정의 뷰 값이 변경될 때 호출됩니다."""
        if not self.plotter:
            return

        try:
            if hasattr(self.main_window, 'custom_x_spin'):
                x = self.main_window.custom_x_spin.value()
                y = self.main_window.custom_y_spin.value()
                z = self.main_window.custom_z_spin.value()
                distance = self.main_window.distance_slider.value() / 100.0

                viewport_data = {"x": x, "y": y, "z": z, "distance": distance}
                self.apply_viewport_from_data(viewport_data)

        except Exception as e:
            print(f"사용자 정의 뷰 변경 오류: {e}")

    def apply_custom_view(self):
        """사용자 정의 뷰를 적용합니다."""
        if not self.plotter:
            return

        try:
            if hasattr(self.main_window, 'custom_x_spin'):
                x = self.main_window.custom_x_spin.value()
                y = self.main_window.custom_y_spin.value()
                z = self.main_window.custom_z_spin.value()
                distance = self.main_window.distance_slider.value() / 100.0

                viewport_data = {"x": x, "y": y, "z": z, "distance": distance}
                self.apply_viewport_from_data(viewport_data)

        except Exception as e:
            print(f"사용자 정의 뷰 적용 오류: {e}")

    def on_distance_slider_changed(self, value: int):
        """
        거리 슬라이더 값 변경 이벤트 처리

        Args:
            value: 슬라이더 값 (0-100)
        """
        if not self.plotter:
            return

        try:
            distance = value / 100.0
            
            position = np.array(self.plotter.camera.position)
            focal_point = np.array(self.plotter.camera.focal_point)
            view_direction = focal_point - position
            view_direction = view_direction / np.linalg.norm(view_direction)

            new_position = focal_point - view_direction * distance
            self.plotter.camera.position = new_position
            self.plotter.render()

        except Exception as e:
            print(f"거리 슬라이더 변경 오류: {e}")

    def set_view_mode(self, mode: str):
        """
        뷰 모드를 설정합니다.
        3D 뷰어의 렌더링 스타일을 변경합니다.
        Args:
            mode (str): 뷰 모드 ("shading", "edges", "wireframe")
        """
        if not self.plotter:
            QtWidgets.QMessageBox.warning(self.main_window, "알림", "3D 모델을 먼저 불러와야 합니다.")
            return

        # 모든 뷰 모드 버튼의 체크 해제
        if hasattr(self.main_window, 'shading_btn'):
            self.main_window.shading_btn.setChecked(False)
        if hasattr(self.main_window, 'edges_btn'):
            self.main_window.edges_btn.setChecked(False)
        if hasattr(self.main_window, 'wireframe_btn'):
            self.main_window.wireframe_btn.setChecked(False)

        # 선택된 모드만 체크
        if mode == "shading":
            if hasattr(self.main_window, 'shading_btn'):
                self.main_window.shading_btn.setChecked(True)
        elif mode == "edges":
            if hasattr(self.main_window, 'edges_btn'):
                self.main_window.edges_btn.setChecked(True)
        elif mode == "wireframe":
            if hasattr(self.main_window, 'wireframe_btn'):
                self.main_window.wireframe_btn.setChecked(True)

        print(f"뷰 모드 설정: {mode}")

        try:
            # PyVista의 이름 기반 actor 쌍을 사용
            # main_surface: 메인 표면 mesh
            # feature_edges: 모서리선 곡선 mesh (30도 각도 기준)
            main_actor = self.plotter.renderer.actors.get("main_surface")
            edges_actor = self.plotter.renderer.actors.get("feature_edges")

            if mode == "shading":
                # 음영처리 모드: 메쉬만 표시, feature edges 숨기기
                if main_actor:
                    main_actor.SetVisibility(True)
                if edges_actor:
                    edges_actor.SetVisibility(False)
                print(f"  → 음영처리: 메쉬만 표시")

            elif mode == "edges":
                # 모서리 표시 음영 모드: 메쉬 + feature edges 표시
                if main_actor:
                    main_actor.SetVisibility(True)
                if edges_actor:
                    edges_actor.SetVisibility(True)
                print(f"  → 모서리 표시 음영: 메쉬 + feature edges 표시")

            elif mode == "wireframe":
                # 와이어프레임 모드: feature edges만 표시 (메쉬 숨김)
                if main_actor:
                    main_actor.SetVisibility(False)
                if edges_actor:
                    edges_actor.SetVisibility(True)
                print(f"  → 와이어프레임: feature edges만 표시")

            # 화면 갱신
            self.plotter.render()

        except Exception as e:
            print(f"뷰 모드 설정 오류: {e}")

    def change_background_color(self):
        """배경색을 변경합니다."""
        if not self.plotter:
            return

        try:
            color = QtWidgets.QColorDialog.getColor(
                QtCore.Qt.white, self.main_window, "배경색 선택"
            )
            if color.isValid():
                self.plotter.background_color = color.name()
                self.plotter.render()

        except Exception as e:
            print(f"배경색 변경 오류: {e}")

    def reset_colors(self):
        """색상을 초기화합니다."""
        if not self.plotter:
            return

        try:
            self.plotter.background_color = "white"
            self.plotter.render()

        except Exception as e:
            print(f"색상 초기화 오류: {e}")

    def change_transparency(self, value: int):
        """
        투명도를 변경합니다.

        Args:
            value: 투명도 값 (0-100)
        """
        if not self.plotter:
            return

        try:
            self.current_transparency = value / 100.0

            # main_surface actor의 투명도를 변경
            main_actor = self.plotter.renderer.actors.get("main_surface")
            if main_actor:
                main_actor.GetProperty().SetOpacity(1.0 - self.current_transparency)

            # 투명도 라벨 업데이트
            if hasattr(self.main_window, 'transparency_label'):
                self.main_window.transparency_label.setText(f"{value}%")

            # 화면 갱신
            self.plotter.render()
            print(f"투명도 설정: {value}%")

        except Exception as e:
            print(f"투명도 변경 오류: {e}")

    def reset_3d_colors(self):
        """3D 색상을 초기화합니다."""
        if not self.plotter:
            return

        try:
            self.plotter.background_color = "white"
            self.current_transparency = 0
            self.plotter.render()

        except Exception as e:
            print(f"3D 색상 초기화 오류: {e}")

    def _get_target_item(self, row: int):
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

    def clear_3d_viewer(self):
        """3D 뷰어를 초기화합니다."""
        if self.plotter:
            try:
                self.plotter.clear()
                self.plotter = None
            except Exception as e:
                print(f"3D 뷰어 초기화 오류: {e}")

    def setup_3d_viewer_color_controls(self):
        """3D 뷰어 색상 컨트롤을 설정합니다."""
        # 색상 컨트롤 설정 로직
        pass
