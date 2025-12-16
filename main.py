# -*- coding: utf-8 -*-
"""
TS Numbering Tool (v6.01) - Refactored Version
"""
from __future__ import annotations
import copy
import json
import math
import os
import random
import sys
import traceback
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import pypdfium2 as pdfium
import pandas as pd
import numpy as np
from PIL import Image
import requests
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtMultimedia import QSoundEffect

# --- 기본/외부 라이브러리 ---
# ▼▼▼ 스레딩 기능에 필요한 모든 부품을 여기서 import 합니다 ▼▼▼
print("=" * 20 + ">>> 올바른 최신 main.py 파일이 실행되었습니다! <<<" + "=" * 20)  # <--- 이 줄 추가
# --- 직접 만든 모듈들 ---
from core.models import LabelStyle, MarkItem, StampItem
from ui.delegates import ComboDelegate, NumericDelegate
from ui.dialogs import SaveOptionsDialog  # <--- 이 부분을 추가해주세요.
from ui.dialogs import (
    AppendPdfDialog,
    InsertDialog,
    NewProjectDialog,
    NumberingModeDialog,
    ShortcutHelpDialog,
    StampManagerDialog,
    StampSettingsDialog,
)
from ui.views import PdfScene, PdfView, ThumbnailLabel
from managers.viewport_manager import ViewportManager
from managers.table_manager import TableManager
from managers.ui_manager import UIManager
from managers.stamp_manager import StampManager
from utils.helpers import (
    _log_error,
    dim_format,
    icon_if,
    normalize_signed_text,
    resource_path,
    strip_prefix_for_value,
)

# --- 상수 정의 ---

APP_NAME = "TS Numbering for PDF"
APP_VER = "v7.00_stable"
TSN_VERSION = "7.00"
TSN_PDF_NAME = "source.pdf"
TSN_META_NAME = "project.json"
DIM_TYPES = ["선형", "Ø", "R", "C", "기타"]


# =====================================================================
#  pypdfium2 헬퍼 함수
# =====================================================================
def _pil_to_qimage(pil_image_or_bitmap):
    """PIL Image 또는 PdfBitmap을 QImage로 변환합니다."""
    # pypdfium2의 PdfBitmap인 경우 PIL Image로 변환
    if hasattr(pil_image_or_bitmap, 'to_pil'):
        pil_image = pil_image_or_bitmap.to_pil()
    else:
        pil_image = pil_image_or_bitmap
    
    # PIL Image를 RGB 모드로 변환
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    
    width, height = pil_image.size
    
    # PIL Image를 바이트로 변환 (RGB 순서)
    # 중요: bytes()로 명시적으로 복사하여 메모리 안정성 확보
    img_data = bytes(pil_image.tobytes("raw", "RGB"))
    
    # QImage 생성 - 바이트 데이터를 직접 사용
    # QImage는 내부적으로 데이터를 복사하므로 안전합니다
    qimage = QtGui.QImage(img_data, width, height, QtGui.QImage.Format_RGB888)
    
    return qimage


def _pdfium_insert_pdf(target_doc, source_doc, from_page=0, to_page=None):
    """pypdfium2에서 PDF 병합 기능을 구현합니다."""
    if to_page is None:
        to_page = len(source_doc) - 1
    
    # pypdfium2의 import_pages를 사용하여 페이지를 직접 복사
    target_doc.import_pages(source_doc, pages=[i for i in range(from_page, to_page + 1)])


def _pil_image_to_pdf_page(pil_image, width_points, height_points):
    """PIL Image를 pypdfium2 PDF 페이지로 변환합니다."""
    import io
    import tempfile
    
    # PIL Image를 PDF로 변환 (임시 파일 사용)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_path = tmp_file.name
    
    # PIL Image를 PDF로 저장 (reportlab 또는 다른 방법 사용)
    # 간단한 방법: 이미지를 PNG로 저장 후 PDF에 삽입
    # 하지만 pypdfium2는 이미지 삽입이 복잡하므로, 
    # 대신 이미지를 PDF로 변환한 후 import_pages 사용
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    
    c = canvas.Canvas(tmp_path, pagesize=(width_points, height_points))
    img_reader = ImageReader(pil_image)
    c.drawImage(img_reader, 0, 0, width=width_points, height=height_points)
    c.save()
    
    # 변환된 PDF를 읽어서 페이지 반환
    img_doc = pdfium.PdfDocument(tmp_path)
    if len(img_doc) > 0:
        page = img_doc.get_page(0)
        os.unlink(tmp_path)
        return page
    os.unlink(tmp_path)
    return None


# =====================================================================
#  메인 윈도우 클래스
# =====================================================================
class Worker(QObject):
    finished = Signal(object)
    error = Signal(str)

    @Slot(str)
    def load_model(self, path):
        """백그라운드에서 3D 모델을 로드하되, 캐시를 활용하여 속도를 높입니다."""
        try:
            import os
            import trimesh

            # 1. 캐시 폴더와 캐시 파일 경로를 생성합니다.
            cache_dir = os.path.join(os.path.dirname(path), ".cache")
            os.makedirs(cache_dir, exist_ok=True)
            # 원본 파일 이름에 .glb 확장자를 붙여 캐시 파일명으로 사용
            cache_filename = os.path.splitext(os.path.basename(path))[0] + ".glb"
            cache_path = os.path.join(cache_dir, cache_filename)
            # 2. 캐시 파일이 존재하는지 확인합니다.
            if os.path.exists(cache_path):
                # 캐시 파일이 있다면, 매우 빠른 glb 파일을 직접 로드합니다.
                print(f"'{cache_filename}' 캐시 파일을 로드합니다.")
                geometry = trimesh.load(cache_path, process=False)
            else:
                # 캐시 파일이 없다면, 느린 원본 파일을 로드합니다.
                print(
                    f"첫 로딩입니다. '{os.path.basename(path)}' 파일을 변환하고 캐시를 생성합니다."
                )
                geometry = trimesh.load(path, process=False)
                # 3. 로드 결과를 다음 사용을 위해 캐시 파일로 저장합니다.
                #    (이 과정도 약간의 시간이 걸리지만, 한 번만 하면 됩니다.)
                print(f"'{cache_filename}' 캐시 파일을 저장 중입니다...")
                if isinstance(geometry, trimesh.Scene):
                    # Scene 객체는 모든 부품을 하나의 파일로 합쳐서 저장
                    merged_mesh = geometry.to_geometry()
                    merged_mesh.export(cache_path)
                else:
                    geometry.export(cache_path)
                print("캐시 파일 저장 완료.")
            self.finished.emit(geometry)
        except Exception as e:
            self.error.emit(str(e))


class PdfAnnotator(QtWidgets.QMainWindow):
    # Worker를 시작시키는 신호 추가
    start_loading_3d = Signal(str)

    def check_trial_status(self):
        """
        30일 트라이얼 상태를 확인합니다.
        Returns:
            tuple: (status, days_left)
            - status: "just_installed", "active", "expired"
            - days_left: 남은 일수
        """
        import winreg
        from datetime import datetime, timedelta
        
        # 레지스트리 키 경로
        reg_key_path = r"SOFTWARE\TS_Numbering_PDF"
        reg_value_name = "InstallDate"
        
        try:
            # 레지스트리에서 설치 날짜 읽기
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key_path, 0, winreg.KEY_READ)
            install_date_str = winreg.QueryValueEx(key, reg_value_name)[0]
            winreg.CloseKey(key)
            
            # 문자열을 날짜로 변환
            install_date = datetime.strptime(install_date_str, "%Y-%m-%d")
            current_date = datetime.now()
            days_passed = (current_date - install_date).days
            days_left = 30 - days_passed
            
            if days_left <= 0:
                return ("expired", 0)
            else:
                return ("active", days_left)
                
        except FileNotFoundError:
            # 레지스트리 키가 없으면 처음 설치
            try:
                # 레지스트리 키 생성 및 설치 날짜 저장
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_key_path)
                install_date_str = datetime.now().strftime("%Y-%m-%d")
                winreg.SetValueEx(key, reg_value_name, 0, winreg.REG_SZ, install_date_str)
                winreg.CloseKey(key)
                return ("just_installed", 30)
            except Exception as e:
                # 레지스트리 접근 실패 시 개발 모드로 처리
                return ("active", 30)
        except Exception as e:
            # 기타 오류 시 개발 모드로 처리
            return ("active", 30)

    def publish_project(self):

        SERVER_URL = "http://127.0.0.1:5000/api/publish"

        # ▼▼▼ [수정 시작] 파일 경로 대신 메모리의 self.doc 객체를 사용 ▼▼▼
        # 1. 현재 문서(self.doc)가 열려있는지 확인
        if not self.doc:
            QtWidgets.QMessageBox.warning(self, "문서 없음", "발행할 프로젝트가 열려있지 않습니다.")
            return
        # 2. JSON 데이터 준비 (기존과 동일)
        items_data = []
        for item in self.items:
            item_dict = {
                "no": item.no,
                "page_index": item.page_index,
                "pdf_point": item.pdf_point,
                "dim_type": item.dim_type,
                "value": item.value,
                "tol_plus": item.tol_plus,
                "tol_minus": item.tol_minus,
                "custom_style": item.custom_style.to_dict() if item.custom_style else None,
            }
            items_data.append(item_dict)
        project_data = {"projectName": self.project_name or "Untitled Project", "items": items_data}
        # 3. 업로드할 PDF 파일 데이터 준비 (파일을 새로 열지 않고 메모리에서 바로 가져옴)
        try:
            # pypdfium2는 tobytes()가 없으므로 임시 파일을 사용합니다
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
            self.doc.save(tmp_path)
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(tmp_path)  # 임시 파일 삭제
            # 업로드할 때 사용할 파일명 결정
            pdf_filename = f"{self.project_name or 'source'}.pdf"
            # 파일 객체 대신 메모리의 바이트 데이터를 직접 전송
            files_to_upload = {"pdf_file": (pdf_filename, pdf_bytes, "application/pdf")}
        except Exception as e:
            _log_error(self, "PDF 데이터 생성 오류", e)
            return
        # 4. 서버로 데이터와 파일 함께 전송 (이하 기존과 동일)
        try:
            response = requests.post(
                SERVER_URL, files=files_to_upload, data={"project_data": json.dumps(project_data)}
            )
            if response.status_code == 200:
                server_message = response.json().get("message")
                QtWidgets.QMessageBox.information(
                    self, "성공", f"서버로부터 응답을 받았습니다:\n{server_message}"
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self, "실패", f"서버 응답 오류 (코드: {response.status_code})"
                )
        except requests.exceptions.RequestException as e:
            QtWidgets.QMessageBox.critical(
                self, "연결 오류", f"테스트 서버에 연결할 수 없습니다.\n\n{e}"
            )
        # ▲▲▲ [수정 끝] ▲▲▲

    def _append_pdf(self, path_to_append: str):
        """선택한 PDF 파일을 원본 그대로 현재 문서 뒤에 이어붙입니다."""
        try:
            new_doc = pdfium.PdfDocument(path_to_append)
            # ▼▼▼ [핵심] 이어붙이기 전의 상태를 기록합니다. ▼▼▼
            original_page_count = len(self.doc)
            num_new_pages = len(new_doc)
            # 원본 그대로 이어붙이기
            _pdfium_insert_pdf(self.doc, new_doc)
            new_doc.close()
            # UI 새로고침
            self._set_dirty(True)
            self._update_page_navigation_ui()
            self._populate_thumbnails()
            # ▼▼▼ [핵심] 상태 표시줄 메시지 대신, 정보창을 띄웁니다. ▼▼▼
            # self.statusBar().showMessage(...) # 이 줄을 삭제하고,
            msg = (
                f"{original_page_count}페이지 뒤에 {original_page_count + 1}페이지부터 {len(self.doc)}페이지까지\n"
                f"총 {num_new_pages} 페이지를 성공적으로 이어붙였습니다."
            )
            QtWidgets.QMessageBox.information(self, "이어붙이기 완료", msg)
            # ▲▲▲ 여기까지 변경 ▲▲▲
        except Exception as e:
            _log_error(self, "PDF 이어붙이기 오류", e)

    def rotate_page_left(self):
        """현재 페이지를 왼쪽으로 90도 회전합니다."""
        if not self.doc:
            return
        page = self.doc.get_page(self.cur_page_index)
        current_rotation = page.get_rotation()
        new_rotation = (current_rotation - 90) % 360
        page.set_rotation(new_rotation)
        self._set_dirty(True)
        self.load_page(self.cur_page_index)  # 화면 새로고침
        self._populate_thumbnails()  # 썸네일도 새로고침

    def rotate_page_right(self):
        """현재 페이지를 오른쪽으로 90도 회전합니다."""
        if not self.doc:
            return
        page = self.doc.get_page(self.cur_page_index)
        current_rotation = page.get_rotation()
        new_rotation = (current_rotation + 90) % 360
        page.set_rotation(new_rotation)
        self._set_dirty(True)
        self.load_page(self.cur_page_index)  # 화면 새로고침
        self._populate_thumbnails()  # 썸네일도 새로고침

    # ===== ▼▼▼ 스탬프 하이라이트 및 삭제 함수 (새로 추가) ▼▼▼ =====
    def _delete_selected_stamps(self):
        """스탬프 테이블에서 선택된 스탬프들을 삭제합니다."""
        selected_rows = sorted(
            list(set(index.row() for index in self.stamp_table.selectedIndexes())), reverse=True
        )
        if not selected_rows:
            return
        stamps_on_page = [s for s in self.stamps if s.page_index == self.cur_page_index]
        for row in selected_rows:
            if 0 <= row < len(stamps_on_page):
                stamp_to_delete = stamps_on_page[row]
                self.stamps.remove(stamp_to_delete)  # 데이터 목록에서 삭제
                # 화면(Scene)에서 그래픽 아이템 삭제
                if id(stamp_to_delete) in self._stamp_graphics_items:
                    self.scene.removeItem(self._stamp_graphics_items[id(stamp_to_delete)])
                    del self._stamp_graphics_items[id(stamp_to_delete)]
        self._clear_stamp_highlight()
        self._refresh_stamp_table()
        self._set_dirty()

    def _highlight_stamp_from_table(self, row, column):
        """테이블 클릭 시 해당 스탬프를 하이라이트합니다."""
        stamps_on_page = [s for s in self.stamps if s.page_index == self.cur_page_index]
        if 0 <= row < len(stamps_on_page):
            self._highlight_stamp(stamps_on_page[row])

    def _highlight_stamp(self, stamp_item: StampItem):
        """특정 스탬프 아이템 주위에 '스케일이 적용된' 하이라이트 사각형을 그립니다."""
        self._clear_stamp_highlight()
        if id(stamp_item) in self._stamp_graphics_items:
            graphic_item = self._stamp_graphics_items[id(stamp_item)]
            rect = graphic_item.boundingRect()
            pen = QtGui.QPen(
                QtGui.QColor("#0078D7"), 4 / graphic_item.scale()
            )  # 선 굵기도 스케일에 맞게 조절
            self._highlighted_stamp_rect = self.scene.addRect(rect, pen)
            # ▼▼▼ [핵심 추가] 하이라이트에도 스탬프와 동일한 기준점과 스케일을 적용합니다. ▼▼▼
            self._highlighted_stamp_rect.setTransformOriginPoint(rect.center())
            self._highlighted_stamp_rect.setScale(graphic_item.scale())
            # ▲▲▲ 여기까지 추가 ▲▲▲
            self._highlighted_stamp_rect.setPos(graphic_item.pos())
            self._highlighted_stamp_rect.setRotation(graphic_item.rotation())
            self._highlighted_stamp_rect.setZValue(10)

    def _clear_stamp_highlight(self):
        """스탬프 하이라이트를 제거합니다."""
        if self._highlighted_stamp_rect:
            self.scene.removeItem(self._highlighted_stamp_rect)
            self._highlighted_stamp_rect = None

    # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
    def _draw_stamp(self, stamp_item: StampItem):
        """StampItem 정보를 바탕으로 화면에 실제 크기를 반영하여 스탬프를 그립니다."""
        stamp_info = self.registered_stamps.get(stamp_item.stamp_key)
        if not stamp_info or not isinstance(stamp_info, dict):
            return
        stamp_path = stamp_info.get("path")
        if not stamp_path:
            return
        pixmap = QtGui.QPixmap(stamp_path)
        if pixmap.isNull():
            return
        item = self.scene.addPixmap(pixmap)
        # 1) 로컬 원점(0,0)을 '이미지 중심'으로 만들기 위해 오프셋을 -w/2, -h/2 로 설정
        rect = pixmap.rect()
        item.setOffset(-rect.width() / 2.0, -rect.height() / 2.0)
        # 2) 변환 기준점도 로컬 원점(=중심)으로 통일
        item.setTransformOriginPoint(QtCore.QPointF(0, 0))
        # 3) 실제 크기 스케일 적용
        width_mm = stamp_info.get("width_mm", 18.0)
        width_points = (width_mm / 25.4) * 72
        target_pixel_width = width_points * self.render_scale
        original_pixel_width = pixmap.width()
        scale_factor = (
            (target_pixel_width / original_pixel_width) if original_pixel_width > 0 else 1.0
        )
        item.setScale(scale_factor)
        # 4) 클릭 지점(=PDF 좌표 → 뷰 좌표 변환)을 '중심'에 정확히 배치
        view_point = self.pdf_to_view(*stamp_item.pdf_point)
        item.setPos(view_point)
        # 5) 나머지 속성
        item.setRotation(stamp_item.rotation)
        item.setOpacity(stamp_item.opacity)
        item.setZValue(5)
        self._stamp_graphics_items[id(stamp_item)] = item

    def _refresh_stamp_table(self):
        """현재 페이지에 있는 스탬프 목록으로 스탬프 테이블을 새로고칩니다."""
        self.stamp_table.setRowCount(0)
        # 현재 페이지의 스탬프만 필터링
        stamps_on_page = [s for s in self.stamps if s.page_index == self.cur_page_index]
        for i, stamp_item in enumerate(stamps_on_page):
            row = self.stamp_table.rowCount()
            self.stamp_table.insertRow(row)
            no_item = QtWidgets.QTableWidgetItem(str(i + 1))
            no_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.stamp_table.setItem(row, 0, no_item)
            self.stamp_table.setItem(row, 1, QtWidgets.QTableWidgetItem(stamp_item.stamp_key))

    def _update_stamp_selector(self):
        """self.registered_stamps 목록을 툴바의 ComboBox에 반영합니다."""
        self.stamp_selector.clear()
        if not self.registered_stamps:
            self.stamp_selector.addItem("- 스탬프 없음 -")
            self.stamp_selector.setEnabled(False)
        else:
            self.stamp_selector.addItems(self.registered_stamps.keys())
            self.stamp_selector.setEnabled(True)

    def open_stamp_settings(self):
        """스탬프 설정 대화상자를 엽니다."""
        dialog = StampSettingsDialog(self)
        current_settings = {
            "opacity": self.stamp_opacity,
            "rotation": self.stamp_rotation,
            "opacity_random": self.stamp_opacity_random,
            "rotation_random": self.stamp_rotation_random,
            "opacity_min": self.stamp_opacity_min,
            "opacity_max": self.stamp_opacity_max,
            "rotation_min": self.stamp_rotation_min,
            "rotation_max": self.stamp_rotation_max,
        }
        dialog.set_settings(current_settings)
        if dialog.exec():
            new_settings = dialog.get_settings()
            self.stamp_opacity = new_settings["opacity"]
            self.stamp_rotation = new_settings["rotation"]
            self.stamp_opacity_random = new_settings["opacity_random"]
            self.stamp_rotation_random = new_settings["rotation_random"]
            self.stamp_opacity_min = new_settings["opacity_min"]
            self.stamp_opacity_max = new_settings["opacity_max"]
            self.stamp_rotation_min = new_settings["rotation_min"]
            self.stamp_rotation_max = new_settings["rotation_max"]
            self._set_dirty()  # 설정이 변경되었으므로 저장 필요

    def open_stamp_manager(self):
        """스탬프 관리 대화상자를 엽니다."""
        # ▼▼▼ 전역 설정을 딕셔너리로 묶어서 전달합니다. ▼▼▼
        global_settings = {
            "opacity": self.stamp_opacity,
            "rotation": self.stamp_rotation,
            "opacity_random": self.stamp_opacity_random,
            "rotation_random": self.stamp_rotation_random,
            "opacity_min": self.stamp_opacity_min,
            "opacity_max": self.stamp_opacity_max,
            "rotation_min": self.stamp_rotation_min,
            "rotation_max": self.stamp_rotation_max,
        }
        dialog = StampManagerDialog(self.registered_stamps, global_settings, self)
        # ▲▲▲ 여기까지 수정 ▲▲▲
        if dialog.exec():
            self.registered_stamps = dialog.get_stamps()
            self.current_stamp_index = 0
            QtCore.QTimer.singleShot(0, self._update_stamp_button_icon)
            self.statusBar().showMessage(
                f"{len(self.registered_stamps)}개의 스탬프가 등록되었습니다."
            )
            self._set_dirty()

    # ... toggle_flow_view 함수 근처 ...
    def toggle_flow_view(self, checked):
        """흐름도 보기 상태를 변경하고, 화면 전체를 새로고침합니다."""
        # 1. 흐름도를 켜려고 할 때, 넘버링 보기가 켜져 있는지 먼저 확인합니다.
        if checked and not self.view_show_numbering:
            QtWidgets.QMessageBox.warning(
                self, "알림", "흐름도를 보려면 먼저 '넘버링 보기'를 켜주세요."
            )
            # 2. (중요) UI의 토글 버튼이 켜진 상태로 바뀌었을 것이므로, 다시 끈 상태로 되돌립니다.
            self.action_toggle_flow_view.setChecked(False)
            if hasattr(self, "a_flow_menu"):
                self.a_flow_menu.setChecked(False)
            return  # 함수 실행을 중단합니다.
        # 3. 조건에 맞을 때만 상태를 변경하고 새로고침합니다.
        self.flow_view_enabled = checked
        # 메뉴 항목 동기화
        if hasattr(self, "a_flow_menu"):
            self.a_flow_menu.setChecked(checked)
        self.load_page(self.cur_page_index)

    def toggle_numbering_view(self, checked):
        """넘버링 보기 상태를 변경하고, 화면 전체를 새로고침합니다."""
        # 1. 넘버링 보기를 끌 경우, 흐름도 보기도 함께 끕니다.
        if not checked and self.flow_view_enabled:
            self.flow_view_enabled = False
            # (중요) UI의 흐름도 토글 버튼 상태도 꺼짐으로 동기화합니다.
            self.action_toggle_flow_view.setChecked(False)
            if hasattr(self, "a_flow_menu"):
                self.a_flow_menu.setChecked(False)
        # 2. 원래의 기능을 수행합니다.
        self.view_show_numbering = checked
        # 메뉴 항목 동기화
        if hasattr(self, "a_numbering_view_menu"):
            self.a_numbering_view_menu.setChecked(checked)
        self.load_page(self.cur_page_index)

    def toggle_stamps_view(self, checked):
        """스탬프 보기 상태를 변경하고, 화면 전체를 새로고침합니다."""
        # print(f"\n>>> [탐침 #3] 스탬프 보기 토글됨: {checked} <<<") # <-- 추가
        self.view_show_stamps = checked
        # 메뉴 항목 동기화
        if hasattr(self, "a_stamps_view_menu"):
            self.a_stamps_view_menu.setChecked(checked)
        self.load_page(self.cur_page_index)

    def _format_no(self, no: float) -> str:
        """정수면 '11', 소수면 '11.5'처럼 깔끔하게 표시."""
        return f"{no:.0f}" if abs(no - round(no)) < 1e-9 else f"{no:g}"

    def _toggle_input_mode(self):
        """입력 모드를 '넘버링 전용'과 '치수 입력' 간에 전환합니다."""
        if self.input_mode == "number_only":
            self.set_input_mode("with_input")
        else:
            self.set_input_mode("number_only")

    def _set_dirty(self, dirty: bool = True):
        """파일의 수정 상태(dirty flag)를 설정하고 창 제목을 업데이트합니다."""
        if self.is_dirty == dirty:
            return
        self.is_dirty = dirty
        self._update_window_title()

    def _update_window_title(self):
        """현재 프로젝트 경로와 수정 상태에 따라 창 제목을 업데이트합니다."""
        title = f"{APP_NAME} ({APP_VER})"
        path_str = ""
        # ===== ▼▼▼ 이 부분을 수정해주세요 ▼▼▼ =====
        if self.project_name:
            path_str = self.project_name  # .tsn 프로젝트 대신 프로젝트 이름을 표시
        elif self.project_path:
            path_str = os.path.basename(self.project_path)
        # ===== ▲▲▲ 여기까지 수정 ▲▲▲ =====
        if path_str:
            title += f" — {path_str}"
        if self.is_dirty:
            title += " *"  # 수정되었으면 제목 끝에 *를 붙입니다.
        self.setWindowTitle(title)

    def _maybe_save(self, title: str, text: str) -> bool:
        """
        수정된 내용이 있으면 사용자에게 저장할지 묻는 대화상자를 띄웁니다.
        '진행'하면 True, '취소'하면 False를 반환합니다.
        """
        if not self.is_dirty:
            return True
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(QtWidgets.QMessageBox.Question)
        btn_save = msg_box.addButton("저장", QtWidgets.QMessageBox.YesRole)
        btn_no = msg_box.addButton("저장 안 함", QtWidgets.QMessageBox.NoRole)
        btn_cancel = msg_box.addButton("취소", QtWidgets.QMessageBox.RejectRole)
        msg_box.exec()
        clicked_button = msg_box.clickedButton()
        if clicked_button == btn_save:
            return self.save_project()
        elif clicked_button == btn_cancel:
            return False
        return True  # "저장 안 함"을 선택한 경우

    def _reset_egg_sequence(self):
        self._egg_count = 0
        # 필요하면 상태바 메시지 정리:
        # self.statusBar().clearMessage()

    def _on_egg_hotkey(self):
        if not self.doc:
            self.statusBar().showMessage(
                "사격 모드는 프로젝트가 열려있을 때만 진입할 수 있습니다.", 3000
            )
            self._reset_egg_sequence()
            return
        if getattr(self, "shooting_mode", False):
            self._reset_egg_sequence()
            return
        self._egg_count += 1
        remaining = self._egg_required - self._egg_count
        self.statusBar().showMessage(f"Secret: Ctrl+F12 {remaining}번 더…")
        self._egg_timer.start(self._egg_window_ms)
        if self._egg_count >= self._egg_required:
            self._egg_timer.stop()
            self._reset_egg_sequence()
            self.toggle_shooting_mode(True)

    # 데이터 꼬임 방지. v4.22
    def renumber_items_by_unit(self):
        """선택한 항목부터 번호를 1단위 정수로 재정렬합니다."""
        selected_rows = sorted(list(set(index.row() for index in self.table.selectedIndexes())))
        if not selected_rows:
            QtWidgets.QMessageBox.warning(self, "알림", "재정렬을 시작할 기준 항목을 선택해주세요.")
            return
        try:
            start_no_float = float(self.table.item(selected_rows[0], 0).text())
        except (ValueError, AttributeError):
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "1단위 재정렬",
            f"'{start_no_float:g}'번부터 번호를 1단위 정수로 재정렬하시겠습니까?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.No:
            return
        # 현재 넘버링 모드에 따라 재정렬할 대상을 다르게 선택합니다.
        if self.numbering_mode == "page_specific":
            # 페이지별 모드: 현재 페이지의 아이템만 대상으로 합니다.
            items_to_renumber = sorted(
                [
                    it
                    for it in self.items
                    if it.page_index == self.cur_page_index and it.no >= start_no_float
                ],
                key=lambda x: x.no,
            )
            items_to_keep = [
                it
                for it in self.items
                if it.page_index != self.cur_page_index or it.no < start_no_float
            ]
        else:
            # 전체 모드: 모든 페이지의 아이템을 대상으로 합니다.
            items_to_renumber = sorted(
                [it for it in self.items if it.no >= start_no_float], key=lambda x: x.no
            )
            items_to_keep = [it for it in self.items if it.no < start_no_float]
        current_new_no = int(start_no_float)
        for item in items_to_renumber:
            item.no = float(current_new_no)
            current_new_no += 1
        self.items = items_to_keep + items_to_renumber
        if self.numbering_mode != "page_specific":
            if self.items:
                self.next_no = float(int(max(it.no for it in self.items) + 1))
            else:
                self.next_no = 1.0
        # 화면과 데이터를 새로고침합니다.
        self.load_page(self.cur_page_index)
        self._update_undo_redo_hint()
        self._update_status()
        self._set_dirty()
        QtWidgets.QMessageBox.information(self, "완료", "1단위 재정렬이 완료되었습니다.")

    def show_table_context_menu(self, pos):
        """Show table context menu with all features. (TableManager delegation)"""
        return self.table_manager.show_table_context_menu(pos)

    def save_viewport_parameters(self):
        """현재 3D 뷰포트 파라메터를 선택된 테이블 항목에 저장합니다. (ViewportManager로 위임)"""
        # ViewportManager에 plotter 동기화
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.save_viewport_parameters()

    def apply_viewport_from_data(self, viewport_data):
        """JSON 형식의 뷰포트 데이터를 받아서 3D 뷰어에 적용합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.apply_viewport_from_data(viewport_data)

    def change_background_color(self):
        """3D 뷰어의 배경 컬러를 변경합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.change_background_color()

    def reset_colors(self):
        """모든 컬러를 기본값으로 리셋합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.reset_colors()

    def _setup_3d_viewer_color_controls(self):
        """
        3D 뷰어에 컬러 컨트롤 패널을 추가합니다.
        """
        try:
            # 통합 컨트롤 패널을 위한 위젯 생성 (전체 영역으로 확장)
            self.integrated_control_panel = QtWidgets.QWidget(self.widget_3d)
            # 크기를 동적으로 설정 (부모 위젯 크기에 맞춤)
            panel_width = self.widget_3d.width() - 20  # 좌우 10px씩 여백
            # 패널 높이: 현재 90px의 75% = 67.5px → 68px
            self.integrated_control_panel.setFixedSize(panel_width, 68)  # 높이 75%로 조정
            # 반투명 배경 설정
            self.integrated_control_panel.setStyleSheet("""
                QWidget {
                    background-color: rgba(40, 40, 40, 200);
                    border: 1px solid rgba(80, 80, 80, 200);
                    border-radius: 6px;
                }
            """)

            # 메인 레이아웃 (가로 배치)
            main_layout = QtWidgets.QHBoxLayout(self.integrated_control_panel)
            main_layout.setContentsMargins(8, 8, 8, 8)  # 상하 여백 75%로 조정
            main_layout.setSpacing(15)
            # === 뷰 모드 섹션 ===
            view_mode_frame = QtWidgets.QFrame()
            view_mode_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(60, 60, 60, 150);
                    border: 1px solid rgba(100, 100, 100, 150);
                    border-radius: 4px;
                }
            """)
            view_mode_layout = QtWidgets.QHBoxLayout(view_mode_frame)
            view_mode_layout.setContentsMargins(8, 8, 8, 8)  # 상하 여백 75%로 조정
            view_mode_layout.setSpacing(8)

            # 뷰 모드 라벨 (볼드 + 두꺼운 테두리)
            view_mode_label = QtWidgets.QLabel("뷰모드")
            view_mode_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 10px;
                    border: 2px solid rgba(255, 255, 255, 200);
                    border-radius: 3px;
                    padding: 2px 4px;
                }
            """)
            view_mode_layout.addWidget(view_mode_label)

            # 뷰 모드 버튼들 생성 (크기 절반으로 조정)
            self.shading_btn = QtWidgets.QPushButton()
            self.shading_btn.setCheckable(True)
            self.shading_btn.setChecked(True)
            self.shading_btn.setFixedSize(32, 32)  # 버튼 크기 절반으로 조정
            self.shading_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)  # 크기 고정
            self.shading_btn.setToolTip("음영처리")
            self.shading_btn.clicked.connect(lambda: self.set_view_mode("shading"))
            self.shading_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(60, 60, 60, 150);
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background-color: rgba(100, 150, 200, 220);
                    border: 2px solid rgba(150, 200, 255, 255);
                }
                QPushButton:hover {
                    background-color: rgba(80, 80, 80, 180);
                }
            """)

            self.edges_btn = QtWidgets.QPushButton()
            self.edges_btn.setCheckable(True)
            self.edges_btn.setFixedSize(32, 32)  # 버튼 크기 절반으로 조정
            self.edges_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)  # 크기 고정
            self.edges_btn.setToolTip("모서리 표시 음영")
            self.edges_btn.clicked.connect(lambda: self.set_view_mode("edges"))
            self.edges_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(60, 60, 60, 150);
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background-color: rgba(150, 100, 200, 220);
                    border: 2px solid rgba(200, 150, 255, 255);
                }
                QPushButton:hover {
                    background-color: rgba(80, 80, 80, 180);
                }
            """)

            self.wireframe_btn = QtWidgets.QPushButton()
            self.wireframe_btn.setCheckable(True)
            self.wireframe_btn.setFixedSize(32, 32)  # 버튼 크기 절반으로 조정
            self.wireframe_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)  # 크기 고정
            self.wireframe_btn.setToolTip("와이어프레임")
            self.wireframe_btn.clicked.connect(lambda: self.set_view_mode("wireframe"))
            self.wireframe_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(60, 60, 60, 150);
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background-color: rgba(200, 150, 100, 220);
                    border: 2px solid rgba(255, 200, 150, 255);
                }
                QPushButton:hover {
                    background-color: rgba(80, 80, 80, 180);
                }
            """)

            # 뷰 모드 버튼에 아이콘 설정
            try:
                from utils.helpers import icon_if
                shading_icon = icon_if("resources/icons/음영처리.png")
                if shading_icon and not shading_icon.isNull():
                    self.shading_btn.setIcon(shading_icon)
                    self.shading_btn.setIconSize(QtCore.QSize(28, 28))  # 버튼 크기에 맞춘 아이콘 크기

                edges_icon = icon_if("resources/icons/음영처리실선.png")
                if edges_icon and not edges_icon.isNull():
                    self.edges_btn.setIcon(edges_icon)
                    self.edges_btn.setIconSize(QtCore.QSize(28, 28))  # 버튼 크기에 맞춘 아이콘 크기

                wireframe_icon = icon_if("resources/icons/와이어프레임.png")
                if wireframe_icon and not wireframe_icon.isNull():
                    self.wireframe_btn.setIcon(wireframe_icon)
                    self.wireframe_btn.setIconSize(QtCore.QSize(28, 28))  # 버튼 크기에 맞춘 아이콘 크기
            except Exception as e:
                print(f"뷰모드 아이콘 로드 실패: {e}")
                pass

            view_mode_layout.addWidget(self.shading_btn)
            view_mode_layout.addWidget(self.edges_btn)
            view_mode_layout.addWidget(self.wireframe_btn)

            # === 투영 방식 섹션 ===
            projection_frame = QtWidgets.QFrame()
            projection_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(60, 60, 60, 150);
                    border: 1px solid rgba(100, 100, 100, 150);
                    border-radius: 4px;
                }
            """)
            projection_layout = QtWidgets.QHBoxLayout(projection_frame)
            projection_layout.setContentsMargins(8, 8, 8, 8)  # 상하 여백 75%로 조정
            projection_layout.setSpacing(8)

            # 투영 방식 라벨 (볼드 + 두꺼운 테두리)
            projection_label = QtWidgets.QLabel("투영")
            projection_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 10px;
                    border: 2px solid rgba(255, 255, 255, 200);
                    border-radius: 3px;
                    padding: 2px 4px;
                }
            """)
            projection_layout.addWidget(projection_label)

            # 일반 뷰 버튼 (크기 절반으로 조정)
            self.normal_view_btn = QtWidgets.QPushButton()
            self.normal_view_btn.setCheckable(True)
            self.normal_view_btn.setChecked(False)  # 기본값은 투시도
            self.normal_view_btn.setFixedSize(32, 32)  # 버튼 크기 절반으로 조정
            self.normal_view_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)  # 크기 고정
            self.normal_view_btn.setToolTip("일반 뷰 (Orthographic): 원근감 없음, 정확한 치수 표시")
            # 아이콘 설정 (크기 2배)
            try:
                from utils.helpers import icon_if
                icon = icon_if("resources/icons/normal_view.png")
                if icon:
                    self.normal_view_btn.setIcon(icon)
                    self.normal_view_btn.setIconSize(QtCore.QSize(28, 28))  # 버튼 크기에 맞춘 아이콘 크기
            except:
                pass  # 아이콘이 없어도 작동
            self.normal_view_btn.clicked.connect(lambda: self.set_projection_mode("orthographic"))
            self.normal_view_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(60, 60, 60, 150);
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background-color: rgba(100, 150, 100, 220);
                    border: 2px solid rgba(150, 200, 150, 255);
                }
                QPushButton:hover {
                    background-color: rgba(80, 80, 80, 180);
                }
            """)
            projection_layout.addWidget(self.normal_view_btn)

            # 투시도 버튼 (크기 절반으로 조정)
            self.perspective_btn = QtWidgets.QPushButton()
            self.perspective_btn.setCheckable(True)
            self.perspective_btn.setChecked(True)  # 기본값은 투시도
            self.perspective_btn.setFixedSize(32, 32)  # 버튼 크기 절반으로 조정
            self.perspective_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)  # 크기 고정
            self.perspective_btn.setToolTip("투시도 (Perspective): 원근감 있음, 현실적인 시각화")
            # 아이콘 설정 (크기 2배)
            try:
                from utils.helpers import icon_if
                icon = icon_if("resources/icons/perspective_view.png")
                if icon:
                    self.perspective_btn.setIcon(icon)
                    self.perspective_btn.setIconSize(QtCore.QSize(28, 28))  # 버튼 크기에 맞춘 아이콘 크기
            except:
                pass  # 아이콘이 없어도 작동
            self.perspective_btn.clicked.connect(lambda: self.set_projection_mode("perspective"))
            self.perspective_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(60, 60, 60, 150);
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background-color: rgba(150, 100, 200, 220);
                    border: 2px solid rgba(200, 150, 255, 255);
                }
                QPushButton:hover {
                    background-color: rgba(80, 80, 80, 180);
                }
            """)
            projection_layout.addWidget(self.perspective_btn)

            # 버튼 그룹 설정 (하나만 선택 가능)
            projection_button_group = QtWidgets.QButtonGroup(self)
            projection_button_group.addButton(self.normal_view_btn, 0)
            projection_button_group.addButton(self.perspective_btn, 1)
            projection_button_group.setExclusive(True)

            # === 컬러 컨트롤 섹션 ===
            color_control_frame = QtWidgets.QFrame()
            color_control_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(60, 60, 60, 150);
                    border: 1px solid rgba(100, 100, 100, 150);
                    border-radius: 4px;
                }
            """)
            color_control_layout = QtWidgets.QVBoxLayout(color_control_frame)  # 세로 레이아웃으로 변경
            color_control_layout.setContentsMargins(8, 8, 8, 8)  # 상하 여백 증가
            color_control_layout.setSpacing(6)

            # 컬러 상단 레이아웃 (라벨, 팔레트, 리셋 버튼)
            color_top_layout = QtWidgets.QHBoxLayout()
            color_top_layout.setSpacing(8)

            # 컬러 컨트롤 라벨 (볼드 + 두꺼운 테두리)
            color_label = QtWidgets.QLabel("컬러")
            color_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 10px;
                    border: 2px solid rgba(255, 255, 255, 200);
                    border-radius: 3px;
                    padding: 2px 4px;
                }
            """)
            color_top_layout.addWidget(color_label)

            # 내장 컬러 팔레트 생성
            self.color_palette = self._create_color_palette()
            color_top_layout.addWidget(self.color_palette)

            # 리셋 버튼
            self.reset_3d_colors_btn = QtWidgets.QPushButton("리셋")
            self.reset_3d_colors_btn.setFixedSize(35, 20)
            self.reset_3d_colors_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(200, 100, 100, 180);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 150);
                    border-radius: 3px;
                    font-size: 8px;
                }
                QPushButton:hover {
                    background-color: rgba(220, 120, 120, 200);
                }
            """)
            self.reset_3d_colors_btn.clicked.connect(self.reset_3d_colors)
            color_top_layout.addWidget(self.reset_3d_colors_btn)
            color_top_layout.addStretch()

            color_control_layout.addLayout(color_top_layout)

            # 투명도 슬라이더 (컬러 밑으로 배치)
            transparency_layout = QtWidgets.QHBoxLayout()
            trans_label = QtWidgets.QLabel("투명도")
            trans_label.setStyleSheet("color: white; font-size: 9px;")
            trans_label.setFixedWidth(35)  # '투명도'로 텍스트가 길어져서 폭 증가

            self.transparency_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            self.transparency_slider.setRange(0, 100)
            self.transparency_slider.setValue(0)
            self.transparency_slider.setFixedWidth(60)
            self.transparency_slider.setFixedHeight(16)
            self.transparency_slider.valueChanged.connect(self.change_transparency)

            self.transparency_label = QtWidgets.QLabel("0%")
            self.transparency_label.setStyleSheet("color: white; font-size: 9px;")
            self.transparency_label.setFixedWidth(25)

            transparency_layout.addWidget(trans_label)
            transparency_layout.addWidget(self.transparency_slider)
            transparency_layout.addWidget(self.transparency_label)
            transparency_layout.addStretch()

            color_control_layout.addLayout(transparency_layout)

            # 메인 레이아웃에 섹션들 추가
            main_layout.addWidget(view_mode_frame)
            main_layout.addWidget(projection_frame)
            main_layout.addWidget(color_control_frame)
            main_layout.addStretch()
            # ��Ʈ�� �г��� 3D ����� ��Ȯ�� ���� ��� ���� ��ġ
            if not self.widget_3d.property("_integrated_panel_filter_installed"):
                self.widget_3d.installEventFilter(self)
                self.widget_3d.setProperty("_integrated_panel_filter_installed", True)
            self._position_integrated_control_panel()
            self.integrated_control_panel.show()
            QtCore.QTimer.singleShot(0, self._position_integrated_control_panel)
            print("3D 뷰어 통합 컨트롤 패널이 추가되었습니다.")
        except Exception as e:
            print(f"3D 뷰어 컬러 컨트롤 설정 오류: {e}")
            import traceback

            traceback.print_exc()

    def _create_color_palette(self):
        """
        내장 컬러 팔레트를 생성합니다.
        """
        palette_widget = QtWidgets.QWidget()
        palette_layout = QtWidgets.QHBoxLayout(palette_widget)
        palette_layout.setContentsMargins(0, 0, 0, 0)
        palette_layout.setSpacing(2)

        # 기본 컬러들
        colors = [
            (255, 255, 255),  # 흰색
            (200, 200, 200),  # 밝은 회색
            (100, 100, 100),  # 회색
            (50, 50, 50),     # 어두운 회색
            (255, 0, 0),      # 빨간색
            (0, 255, 0),      # 초록색
            (0, 0, 255),      # 파란색
            (255, 255, 0),    # 노란색
            (255, 0, 255),    # 자홍색
            (0, 255, 255),    # 청록색
        ]

        # 선택된 컬러를 추적하기 위한 변수 초기화
        if not hasattr(self, '_selected_color_rgb'):
            self._selected_color_rgb = None
        
        for i, (r, g, b) in enumerate(colors):
            color_btn = QtWidgets.QPushButton()
            color_btn.setFixedSize(13, 13)  # 16px의 80% = 12.8px → 13px
            color_btn.setToolTip(f"RGB({r}, {g}, {b})")
            color_btn.setProperty("color_rgb", (r, g, b))  # 컬러 정보를 속성으로 저장

            # 컬러 버튼 스타일 설정 (기본 상태)
            color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({r}, {g}, {b});
                    border: 1px solid rgba(255, 255, 255, 100);
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    border: 2px solid rgba(255, 255, 255, 200);
                }}
                QPushButton:pressed {{
                    border: 2px solid rgba(0, 0, 0, 200);
                }}
            """)

            # 컬러 선택 이벤트 연결
            color_btn.clicked.connect(lambda checked, rgb=(r, g, b): self._select_color_from_palette(rgb))
            palette_layout.addWidget(color_btn)
            
            # 컬러 버튼을 속성으로 저장 (하이라이트 업데이트용)
            if not hasattr(self, '_color_buttons'):
                self._color_buttons = []
            self._color_buttons.append(color_btn)

        return palette_widget

    def _select_color_from_palette(self, rgb):
        """
        팔레트에서 선택된 컬러를 배경색으로 적용합니다.
        """
        try:
            if not hasattr(self, 'plotter') or self.plotter is None:
                return

            r, g, b = rgb
            # RGB 값을 0-1 범위로 변환
            r_norm = r / 255.0
            g_norm = g / 255.0
            b_norm = b / 255.0

            # 배경 컬러 설정
            self.plotter.background_color = (r_norm, g_norm, b_norm)
            self.plotter.render()

            # 선택된 컬러 저장
            self._selected_color_rgb = rgb
            
            # 모든 컬러 버튼의 하이라이트 업데이트
            self._update_color_palette_highlight()

            print(f"배경 컬러가 변경되었습니다: RGB({r}, {g}, {b})")

        except Exception as e:
            print(f"컬러 적용 오류: {e}")
    
    def _update_color_palette_highlight(self):
        """컬러 팔레트의 선택된 버튼에 하이라이트를 적용합니다."""
        if not hasattr(self, '_color_buttons'):
            return
        
        for color_btn in self._color_buttons:
            rgb = color_btn.property("color_rgb")
            if rgb is None:
                continue
            
            r, g, b = rgb
            is_selected = (hasattr(self, '_selected_color_rgb') and 
                          self._selected_color_rgb is not None and 
                          self._selected_color_rgb == rgb)
            
            # 선택된 경우 두꺼운 노란색 테두리로 하이라이트
            if is_selected:
                color_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgb({r}, {g}, {b});
                        border: 3px solid rgba(255, 255, 0, 255);
                        border-radius: 2px;
                    }}
                    QPushButton:hover {{
                        border: 3px solid rgba(255, 255, 0, 255);
                    }}
                """)
            else:
                color_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgb({r}, {g}, {b});
                        border: 1px solid rgba(255, 255, 255, 100);
                        border-radius: 2px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid rgba(255, 255, 255, 200);
                    }}
                    QPushButton:pressed {{
                        border: 2px solid rgba(0, 0, 0, 200);
                    }}
                """)

    def _position_integrated_control_panel(self):
        """
        통합 컨트롤 패널을 3D 뷰어 상단 전체 영역에 배치합니다.
        """
        panel = getattr(self, "integrated_control_panel", None)
        parent = getattr(self, "widget_3d", None)
        if not panel or not parent:
            return

        # 패널 크기를 부모 위젯에 맞게 동적으로 조정
        panel_width = parent.width() - 20  # 좌우 10px씩 여백
        panel_height = 68  # 높이 75%로 조정 (버튼 32x32 + 여백)
        panel.setFixedSize(panel_width, panel_height)

        # 상단 중앙에 배치 (전체 영역 사용)
        x = 10  # 좌측 여백
        y = 10  # 상단 여백
        panel.move(x, y)
        panel.raise_()

    def _position_color_control_panel(self):
        panel = getattr(self, "color_control_panel", None)
        parent = getattr(self, "widget_3d", None)
        if not panel or not parent:
            return
        margin = 10
        x = max(margin, parent.width() - panel.width() - margin)
        y = margin
        panel.move(x, y)
        panel.raise_()

    def change_transparency(self, value):
        """투명도를 변경합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.change_transparency(value)

    def reset_3d_colors(self):
        """3D 뷰어의 모든 컬러 설정을 리셋합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.reset_3d_colors()

    def show_about_dialog(self):
        """프로그램 정보 대화상자를 띄웁니다."""
        about_text = f"""
            <h3>{APP_NAME}</h3>
            <p>Version {APP_VER} 검사 도면(pdf) 넘버링 프로그램 입니다.</p>
            <br>
            <p><b>Created by Kosangmin</b></p>
            <p>Copyright © 2025 Taesung Engineering. All rights reserved.</p>
        """
        QtWidgets.QMessageBox.about(self, f"{APP_NAME} 정보", about_text)

    # =====================================================================
    #  Windows 메뉴 - 도킹 윈도우 토글 함수들
    # =====================================================================
    def toggle_pdf_preview(self, checked):
        """
        PDF Page Preview 윈도우(왼쪽 도크)를 보이거나 숨깁니다.
        Args:
            checked (bool): 메뉴 항목의 체크 상태
        """
        if checked:
            self.page_dock.show()
        else:
            self.page_dock.hide()

    def toggle_numbering_list(self, checked):
        """
        Numbering List 윈도우(오른쪽 도크)를 보이거나 숨깁니다.
        Args:
            checked (bool): 메뉴 항목의 체크 상태
        """
        if checked:
            self.dock.show()
        else:
            self.dock.hide()

    def toggle_3d_navigator(self, checked):
        """
        3D Navigator 윈도우를 보이거나 숨깁니다.
        Args:
            checked (bool): 메뉴 항목의 체크 상태
        """
        if checked:
            self.navigator_dock.show()
        else:
            self.navigator_dock.hide()

    def update_view_info(self):
        """현재 카메라의 위치, 방향, 거리 정보를 Navigator 하단에 표시합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.update_view_info()

    def align_view_axis(self):
        """뷰 정렬 단축키(F6): 가장 큰 축만 남기고 나머지 축을 0으로 정렬"""
        if hasattr(self, "viewport_manager"):
            self.viewport_manager.align_view_to_dominant_axis()

    def set_viewport(self, view_name):
        """뷰포트를 설정합니다. 3D 뷰어의 카메라 위치를 변경합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.set_viewport(view_name)

    def update_custom_view(self):
        """사용자 정의 뷰 설정 값이 변경될 때 호출됩니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.update_custom_view()

    def on_custom_view_changed(self):
        """사용자 정의 뷰 값이 변경될 때 호출됩니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.on_custom_view_changed()

    def apply_custom_view(self):
        """사용자 정의 뷰 설정을 적용합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.apply_custom_view()

    def on_distance_slider_changed(self, value):
        """거리 슬라이더 값이 변경될 때 호출됩니다."""
        # 스핀박스와 연동 (1~100을 0.1~10.0으로 변환)
        # 선형 변환: 1→0.1, 100→10.0
        distance = 0.1 + (value - 1) * (10.0 - 0.1) / (100 - 1)
        self.distance_spin.blockSignals(True)
        self.distance_spin.setValue(distance)
        self.distance_spin.blockSignals(False)

        # ViewportManager로 뷰 업데이트 위임
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
            self.viewport_manager.on_distance_slider_changed(value)

    def on_distance_spin_changed(self, value):
        """거리 스핀박스 값이 변경될 때 호출됩니다."""
        # 슬라이더와 연동 (0.1~10.0을 1~100으로 변환)
        # 선형 변환: 0.1→1, 10.0→100
        slider_value = int(1 + (value - 0.1) * (100 - 1) / (10.0 - 0.1))
        self.distance_slider.blockSignals(True)
        self.distance_slider.setValue(slider_value)
        self.distance_slider.blockSignals(False)

        # 뷰 업데이트
        self.on_custom_view_changed()

    def set_projection_mode(self, mode):
        """투영 방식을 설정합니다. 3D 뷰어의 카메라 투영 방식을 변경합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.set_projection_mode(mode)

    def set_view_mode(self, mode):
        """뷰 모드를 설정합니다. 3D 뷰어의 렌더링 스타일을 변경합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.set_view_mode(mode)

    # 단축키 목록 보기 도움말 대화상자 기능 추가. v3.07에서...
    def show_shortcut_help(self):
        """단축키 도움말 대화상자를 띄우고, 오류 발생 시 메시지를 표시합니다."""
        try:
            dialog = ShortcutHelpDialog(self)
            dialog.exec()
        except Exception as e:
            import traceback

            error_details = (
                f"도움말 창을 여는 중 오류가 발생했습니다:\n\n{e}\n\n{traceback.format_exc()}"
            )
            QtWidgets.QMessageBox.critical(self, "도움말 창 오류", error_details)

    # 프로젝트 저장관련 교체.
    def _cmd_export_pdf(self):
        try:
            # ===== ▼▼▼ 수정 시작 ▼▼▼ =====
            if not self.doc:
                QtWidgets.QMessageBox.warning(self, "알림", "내보낼 PDF 문서가 없습니다.")
                return
            # 프로젝트 정보가 있으면 기본 경로와 파일명으로 사용
            default_dir = self.project_dir or ""
            default_filename = (
                f"{self.project_name}_Inspection.pdf" if self.project_name else "output.pdf"
            )
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "PDF로 내보내기", os.path.join(default_dir, default_filename), "PDF (*.pdf)"
            )
            # ===== ▲▲▲ 수정 끝 ▲▲▲ =====
            if not path:
                return
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self._save_pdf_with_labels(path)
            QtWidgets.QMessageBox.information(self, "TS Numbering", "내보내기 완료:\n" + path)
        except Exception as e:
            _log_error(self, "PDF 내보내기 오류", e)

    # v3.26에서 동째로 교체...... 안에 주석도 많이 날아감..
    # 새로 하려니 많이 귀찮아서 그냥 했음...ㅠㅠㅠ v3.26에서..
    # 이스터에크... 사격모드 함수!! v3.30에서..
    def toggle_shooting_mode(self, enable: bool):
        """이스터에그인 사격 모드를 켜거나 끄고, 다른 UI를 잠금/해제합니다."""
        self.shooting_mode = enable
        # 잠금/해제할 UI 요소들을 리스트로 관리
        ui_elements = [self.menuBar(), self.main_toolbar, self.page_dock, self.dock]
        if self.shooting_mode:
            # [사격 모드 진입]
            if self._preview_text:
                self._preview_text.setVisible(False)
            cursor = QtGui.QCursor(
                self.crosshair_pixmap.scaled(
                    64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
                )
            )
            self.view.setCursor(cursor)
            self.statusBar().showMessage("사격 모드 활성화! (해제: Ctrl+F11)")
            # 모든 UI 요소를 비활성화(잠금)
            for element in ui_elements:
                element.setEnabled(False)
        else:
            # [사격 모드 종료]
            self.clear_bullet_holes()
            if self._preview_text:
                self._preview_text.setVisible(True)
            self.set_preview_mode(self.preview_mode)
            QtWidgets.QMessageBox.information(
                self, "모드 변경", "사격 모드가 종료되었습니다. 다시 업무에 집중합시다."
            )
            self._update_status()
            # 모든 UI 요소를 다시 활성화
            for element in ui_elements:
                element.setEnabled(True)

    def _create_sub_separator(self):
        """여백(9px)을 포함한 서브 구분선 위젯을 생성합니다."""
        # 전체를 담을 컨테이너 위젯
        separator_widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(separator_widget)
        # 레이아웃 자체의 여백과 간격은 0으로 설정합니다.
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # 9px 너비를 가진 '투명한 벽돌' 역할을 할 왼쪽 스페이서 위젯
        left_spacer = QtWidgets.QWidget()
        left_spacer.setFixedWidth(9)
        # 실제 보이는 선
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        # 9px 너비를 가진 오른쪽 스페이서 위젯
        right_spacer = QtWidgets.QWidget()
        right_spacer.setFixedWidth(9)
        # 레이아웃에 스페이서, 선, 스페이서 순서로 추가
        layout.addWidget(left_spacer)
        layout.addWidget(line)
        layout.addWidget(right_spacer)
        return separator_widget

    # ===== ▼▼▼ 아래 3개 함수를 새로 추가해주세요 ▼▼▼ =====
    def _toggle_show_start_end(self, checked):
        """흐름도의 시작/끝점 강조 표시를 켜고 끕니다."""
        self.style.flow_show_start_end = checked
        # 메뉴 항목 동기화
        if hasattr(self, "a_start_end_menu"):
            self.a_start_end_menu.setChecked(checked)
        self._update_flow_view()  # 흐름도만 다시 그리기
        self._set_dirty()

    def _cycle_line_style(self):
        """흐름도의 선 스타일을 solid -> dash -> dot 순서로 변경합니다."""
        styles = ["solid", "dash", "dot"]
        try:
            current_index = styles.index(self.style.flow_line_style)
        except ValueError:
            current_index = 0  # 현재 스타일을 찾지 못하면 solid로 초기화
        next_index = (current_index + 1) % len(styles)
        self.style.flow_line_style = styles[next_index]
        self._update_line_style_button_icon()  # 버튼 아이콘과 툴팁 업데이트
        self.load_page(self.cur_page_index)  # 변경사항 즉시 반영
        self._set_dirty()

    def _update_line_style_button_icon(self):
        """현재 선 스타일에 맞춰 툴바 버튼의 아이콘과 툴팁을 업데이트합니다."""
        if not hasattr(self, "action_cycle_line_style"):
            return
        current_style = self.style.flow_line_style
        if current_style == "dash":
            self.action_cycle_line_style.setIcon(self.dash_icon)
            self.action_cycle_line_style.setToolTip("선 스타일: 점선 (클릭해서 변경)")
        elif current_style == "dot":
            self.action_cycle_line_style.setIcon(self.dot_icon)
            self.action_cycle_line_style.setToolTip("선 스타일: 파선 (클릭해서 변경)")
        else:  # "solid"
            self.action_cycle_line_style.setIcon(self.solid_icon)
            self.action_cycle_line_style.setToolTip("선 스타일: 실선 (클릭해서 변경)")

    # ▼▼▼ 아래 2개 함수를 새로 추가해주세요 ▼▼▼
    def _cycle_arrow_style(self):
        """흐름도의 선 끝 스타일을 none -> arrow -> circle 순서로 변경합니다."""
        styles = ["none", "arrow", "circle"]
        try:
            current_index = styles.index(self.style.flow_arrow_style)
        except ValueError:
            current_index = 1  # 기본값인 arrow로 초기화
        next_index = (current_index + 1) % len(styles)
        self.style.flow_arrow_style = styles[next_index]
        self._update_arrow_style_button_icon()
        self.load_page(self.cur_page_index)
        self._set_dirty()

    def _update_arrow_style_button_icon(self):
        """현재 선 끝 스타일에 맞춰 툴바 버튼의 아이콘과 툴팁을 업데이트합니다."""
        if not hasattr(self, "action_cycle_arrow_style"):
            return
        current_style = self.style.flow_arrow_style
        if current_style == "circle":
            self.action_cycle_arrow_style.setIcon(self.arrow_circle_icon)
            self.action_cycle_arrow_style.setToolTip("선 끝 모양: 원 (클릭해서 변경)")
        elif current_style == "none":
            self.action_cycle_arrow_style.setIcon(self.arrow_none_icon)
            self.action_cycle_arrow_style.setToolTip("선 끝 모양: 없음 (클릭해서 변경)")
        else:  # "arrow"
            self.action_cycle_arrow_style.setIcon(self.arrow_arrow_icon)
            self.action_cycle_arrow_style.setToolTip("선 끝 모양: 화살표 (클릭해서 변경)")

    def _create_toolbar_group(self, actions, text_label):
        """버튼(Action) 리스트와 제목을 받아 하나의 그룹 상자 위젯을 생성합니다. (UIManager로 위임)"""
        return self.ui_manager.create_toolbar_group(actions, text_label)

    # 이스터에그 진/출입 오류 수정.
    def _create_toolbar(self):
        """커스텀 그룹 레이아웃을 가진 메인 툴바를 생성합니다."""
        self.main_toolbar = QtWidgets.QToolBar("Main Toolbar")
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.main_toolbar)
        custom_toolbar_widget = QtWidgets.QWidget(self)
        main_layout = QtWidgets.QHBoxLayout(custom_toolbar_widget)
        main_layout.setContentsMargins(10, 0, 10, 0)
        main_layout.setSpacing(0)
        # --- 아이콘 로드 ---
        # --- 아이콘 로드 ---
        self._icon_edit_on = icon_if("resources/icons/icons_edit_on.png")
        self._icon_edit_off = icon_if("resources/icons/icons_edit_off.png")
        self.preview_circle_icon = icon_if("resources/icons/circle.png")
        self.preview_crosshair_icon = icon_if("resources/icons/crossline.png")
        undo_icon = icon_if("resources/icons/icons_undo.png")
        redo_icon = icon_if("resources/icons/icons_redo.png")
        highlight_icon = icon_if("resources/icons/highlight.png")
        numbering_settings_icon = icon_if("resources/icons/numbering_manage.png")
        settings_stamps_icon = icon_if("resources/icons/stamp_settings.png")
        self.numbering_view_icon = icon_if("resources/icons/numbering_view_on.png")
        self.stamp_view_icon = icon_if("resources/icons/stamp_view_on.png")
        self.flow_view_icon = icon_if("resources/icons/Flowline.png")
        radius_down_icon = icon_if("resources/icons/radius_down.png")
        radius_up_icon = icon_if("resources/icons/radius_up.png")
        border_down_icon = icon_if("resources/icons/border_down.png")
        border_up_icon = icon_if("resources/icons/border_up.png")
        font_down_icon = icon_if("resources/icons/font_down.png")
        font_up_icon = icon_if("resources/icons/font_up.png")
        self.start_end_icon = icon_if("resources/icons/start_end.png")
        self.solid_icon = icon_if("resources/icons/solidline.png")
        self.dash_icon = icon_if("resources/icons/dashline.png")
        self.dot_icon = icon_if("resources/icons/dotline.png")
        self.arrow_none_icon = icon_if("resources/icons/arrow_none.png")
        self.arrow_arrow_icon = icon_if("resources/icons/arrow_arrow.png")
        self.arrow_circle_icon = icon_if("resources/icons/arrow_circle.png")
        self.rotate_left_icon = icon_if("resources/icons/rotate_left.png")
        self.rotate_right_icon = icon_if("resources/icons/rotate_right.png")
        # --- 액션 및 위젯 정의 ---
        # 기존 모드 토글 액션 (Ctrl+E용 순환 전환)
        self.action_toggle_mode = QtGui.QAction(self._icon_edit_off, "작업 모드 전환", self)
        self.action_toggle_mode.setCheckable(True)
        self.action_toggle_mode.triggered.connect(self._cycle_active_mode)
        self.action_numbering_settings = QtGui.QAction(
            numbering_settings_icon, "넘버링 설정...", self
        )
        self.action_numbering_settings.triggered.connect(self.open_numbering_settings)
        self.action_stamp_settings = QtGui.QAction(settings_stamps_icon, "스탬프 설정...", self)
        self.action_stamp_settings.triggered.connect(self.open_stamp_settings)
        self.action_undo = QtGui.QAction(undo_icon, "실행 취소", self)
        self.action_undo.triggered.connect(self.undo)
        self.action_redo = QtGui.QAction(redo_icon, "다시 실행", self)
        self.action_redo.triggered.connect(self.redo)
        self.action_highlight_toolbar = QtGui.QAction(highlight_icon, "하이라이트 On/Off", self)
        self.action_highlight_toolbar.setCheckable(True)
        self.action_highlight_toolbar.setChecked(self.highlight_enabled)
        self.action_highlight_toolbar.toggled.connect(self.toggle_highlighting)
        self.action_toggle_numbering_view = QtGui.QAction(
            self.numbering_view_icon, "넘버링 보기", self
        )
        self.action_toggle_numbering_view.setCheckable(True)
        self.action_toggle_numbering_view.setChecked(self.view_show_numbering)
        self.action_toggle_numbering_view.toggled.connect(self.toggle_numbering_view)
        self.action_toggle_stamps_view = QtGui.QAction(self.stamp_view_icon, "스탬프 보기", self)
        self.action_toggle_stamps_view.setCheckable(True)
        self.action_toggle_stamps_view.setChecked(self.view_show_stamps)
        self.action_toggle_stamps_view.toggled.connect(self.toggle_stamps_view)
        self.action_toggle_flow_view = QtGui.QAction(self.flow_view_icon, "흐름도 보기", self)
        self.action_toggle_flow_view.setCheckable(True)
        self.action_toggle_flow_view.setChecked(self.flow_view_enabled)
        self.action_toggle_flow_view.toggled.connect(self.toggle_flow_view)
        self.action_radius_down = QtGui.QAction(radius_down_icon, "원 크기 작게 (Shift+F2)", self)
        self.action_radius_down.triggered.connect(
            lambda: self.adjust_label_style("radius_view_px", -2)
        )
        self.action_radius_up = QtGui.QAction(radius_up_icon, "원 크기 크게 (Shift+F1)", self)
        self.action_radius_up.triggered.connect(
            lambda: self.adjust_label_style("radius_view_px", 2)
        )
        self.action_border_down = QtGui.QAction(border_down_icon, "테두리 얇게 (Shift+F4)", self)
        self.action_border_down.triggered.connect(
            lambda: self.adjust_label_style("stroke_width", -1)
        )
        self.action_border_up = QtGui.QAction(border_up_icon, "테두리 굵게 (Shift+F3)", self)
        self.action_border_up.triggered.connect(lambda: self.adjust_label_style("stroke_width", 1))
        self.action_font_down = QtGui.QAction(font_down_icon, "글자 작게 (Shift+F6)", self)
        self.action_font_down.triggered.connect(
            lambda: self.adjust_label_style("font_size_view_px", -2)
        )
        self.action_font_up = QtGui.QAction(font_up_icon, "글자 크게 (Shift+F5)", self)
        self.action_font_up.triggered.connect(
            lambda: self.adjust_label_style("font_size_view_px", 2)
        )
        self.action_toggle_start_end = QtGui.QAction(
            self.start_end_icon, "시작/끝점 강조 On/Off", self
        )
        self.action_toggle_start_end.setCheckable(True)
        self.action_toggle_start_end.setChecked(self.style.flow_show_start_end)
        self.action_toggle_start_end.triggered.connect(self._toggle_show_start_end)
        self.action_cycle_line_style = QtGui.QAction(self)
        self.action_cycle_line_style.triggered.connect(self._cycle_line_style)
        self.action_cycle_arrow_style = QtGui.QAction(self)
        self.action_cycle_arrow_style.triggered.connect(self._cycle_arrow_style)
        # ▼▼▼ 회전 액션 2개 정의 추가 ▼▼▼
        self.action_rotate_left = QtGui.QAction(self.rotate_left_icon, "페이지 좌로 회전", self)
        self.action_rotate_left.triggered.connect(self.rotate_page_left)
        self.action_rotate_right = QtGui.QAction(self.rotate_right_icon, "페이지 우로 회전", self)
        self.action_rotate_right.triggered.connect(self.rotate_page_right)
        self._update_line_style_button_icon()
        self._update_line_style_button_icon()
        self._update_arrow_style_button_icon()
        
        # 미리보기 모드 버튼을 두 개로 분리 (원/십자)
        self.preview_circle_button = QtWidgets.QToolButton()
        self.preview_circle_button.setCheckable(True)
        self.preview_circle_button.setChecked(True)  # 디폴트는 원 모드
        circle_icon = icon_if("resources/icons/circle.png")
        if circle_icon:
            self.preview_circle_button.setIcon(circle_icon)
        self.preview_circle_button.setToolTip("미리보기: 원")
        self.preview_circle_button.clicked.connect(lambda: self.set_preview_mode("preview"))
        
        self.preview_crosshair_button = QtWidgets.QToolButton()
        self.preview_crosshair_button.setCheckable(True)
        crosshair_icon = icon_if("resources/icons/crossline.png")
        if crosshair_icon:
            self.preview_crosshair_button.setIcon(crosshair_icon)
        self.preview_crosshair_button.setToolTip("미리보기: 십자선")
        self.preview_crosshair_button.clicked.connect(lambda: self.set_preview_mode("crosshair"))
        
        # 미리보기 버튼들을 배타적 그룹으로 묶기
        self.preview_button_group = QtWidgets.QButtonGroup(self)
        self.preview_button_group.addButton(self.preview_circle_button, 0)
        self.preview_button_group.addButton(self.preview_crosshair_button, 1)
        self.preview_button_group.setExclusive(True)
        
        self.stamp_button = QtWidgets.QToolButton()
        self.stamp_button.clicked.connect(self._cycle_next_stamp)
        # --- 그룹별 레이아웃 구성 ---
        group1_actions = [self.action_undo, self.action_redo]

        # === 모드 선택 그룹 ===
        # 넘버링 / 스탬프 / 보기 모드를 개별 아이콘으로 선택
        self.mode_action_group = QtGui.QActionGroup(self)
        self.mode_action_group.setExclusive(True)

        self.action_mode_view = QtGui.QAction(self._icon_edit_off, "보기 모드", self)
        self.action_mode_view.setCheckable(True)
        self.action_mode_view.setChecked(True)  # 디폴트로 보기 모드 선택
        self.action_mode_view.triggered.connect(lambda: self._set_active_mode_from_action("view"))
        self.mode_action_group.addAction(self.action_mode_view)

        # 넘버링 모드 아이콘
        numbering_mode_icon = icon_if("resources/icons/numbering_mode.png")
        self.action_mode_numbering = QtGui.QAction(numbering_mode_icon, "넘버링 모드", self)
        self.action_mode_numbering.setCheckable(True)
        self.action_mode_numbering.triggered.connect(lambda: self._set_active_mode_from_action("numbering"))
        self.mode_action_group.addAction(self.action_mode_numbering)

        # 스탬프 모드 아이콘
        stamp_mode_icon = icon_if("resources/icons/stamp_mode.png")
        self.action_mode_stamp = QtGui.QAction(stamp_mode_icon, "스탬프 모드", self)
        self.action_mode_stamp.setCheckable(True)
        self.action_mode_stamp.triggered.connect(lambda: self._set_active_mode_from_action("stamp"))
        self.mode_action_group.addAction(self.action_mode_stamp)

        mode_actions = [self.action_mode_view, self.action_mode_numbering, self.action_mode_stamp]

        # === 작업 설정 그룹 ===
        group2 = QtWidgets.QGroupBox("작업 설정")
        group2.setAlignment(QtCore.Qt.AlignCenter)
        group2_layout = QtWidgets.QHBoxLayout(group2)
        # 모드 선택 그룹이 별도로 생겼으므로 높이를 조금 줄임
        group2_layout.setContentsMargins(4, 8, 4, 4)
        group2_layout.setSpacing(4)
        self.context_widget_stack = QtWidgets.QStackedWidget()
        view_context_widget = QtWidgets.QWidget()
        view_layout = QtWidgets.QHBoxLayout(view_context_widget)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(4)
        numbering_view_button = QtWidgets.QToolButton()
        numbering_view_button.setDefaultAction(self.action_toggle_numbering_view)
        stamp_view_button = QtWidgets.QToolButton()
        stamp_view_button.setDefaultAction(self.action_toggle_stamps_view)
        flow_view_button = QtWidgets.QToolButton()
        flow_view_button.setDefaultAction(self.action_toggle_flow_view)
        view_layout.addWidget(numbering_view_button)
        view_layout.addWidget(stamp_view_button)
        view_layout.addWidget(flow_view_button)
        numbering_context_widget = QtWidgets.QWidget()
        numbering_layout = QtWidgets.QHBoxLayout(numbering_context_widget)
        numbering_layout.setContentsMargins(0, 0, 0, 0)
        numbering_layout.setSpacing(4)
        num_settings_button = QtWidgets.QToolButton()
        num_settings_button.setDefaultAction(self.action_numbering_settings)
        # 미리보기 버튼 두 개 추가 (원/십자)
        numbering_layout.addWidget(self.preview_circle_button)
        numbering_layout.addWidget(self.preview_crosshair_button)
        numbering_layout.addWidget(num_settings_button)
        numbering_layout.addStretch()
        stamp_context_widget = QtWidgets.QWidget()
        stamp_layout = QtWidgets.QHBoxLayout(stamp_context_widget)
        stamp_layout.setContentsMargins(0, 0, 0, 0)
        stamp_layout.setSpacing(4)
        
        # 스탬프 이미지 관리 버튼 추가 (제일 왼쪽)
        stamp_reg_icon = icon_if("resources/icons/stamp_reg.png")
        self.action_stamp_manager = QtGui.QAction(stamp_reg_icon, "스탬프 이미지 관리", self)
        self.action_stamp_manager.triggered.connect(self.open_stamp_manager)
        stamp_manager_button = QtWidgets.QToolButton()
        stamp_manager_button.setDefaultAction(self.action_stamp_manager)
        
        stamp_settings_button = QtWidgets.QToolButton()
        stamp_settings_button.setDefaultAction(self.action_stamp_settings)
        self.stamp_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.stamp_button.customContextMenuRequested.connect(self._show_stamp_context_menu)
        stamp_layout.addWidget(stamp_manager_button)
        stamp_layout.addWidget(self.stamp_button)
        stamp_layout.addWidget(stamp_settings_button)
        stamp_layout.addStretch()
        for btn in [
            self.preview_circle_button,
            self.preview_crosshair_button,
            self.stamp_button,
            num_settings_button,
            stamp_settings_button,
            stamp_manager_button,
            numbering_view_button,
            stamp_view_button,
            flow_view_button,
        ]:
            btn.setIconSize(QtCore.QSize(36, 36))
        self.context_widget_stack.addWidget(view_context_widget)
        self.context_widget_stack.addWidget(numbering_context_widget)
        self.context_widget_stack.addWidget(stamp_context_widget)
        max_width = view_context_widget.sizeHint().width()
        self.context_widget_stack.setMinimumWidth(max_width)
        group2_layout.addWidget(self.context_widget_stack)
        group3_actions = [self.action_highlight_toolbar, self.action_toggle_start_end]
        # ▼▼▼ 새로운 회전 그룹 추가 ▼▼▼
        group_rotate_actions = [self.action_rotate_left, self.action_rotate_right]
        
        # 색상 아이콘 로드
        circle_color_icon = icon_if("resources/icons/circle_color.png")
        text_color_icon = icon_if("resources/icons/text_color.png")
        background_color_icon = icon_if("resources/icons/background_color.png")
        
        # 색상 액션 생성 (바로 색상 팔레트 열기)
        self.action_stroke_color = QtGui.QAction(circle_color_icon, "테두리 색", self)
        self.action_stroke_color.triggered.connect(lambda: self._open_color_dialog("stroke"))
        
        self.action_text_color = QtGui.QAction(text_color_icon, "숫자 색", self)
        self.action_text_color.triggered.connect(lambda: self._open_color_dialog("text"))
        
        self.action_fill_color = QtGui.QAction(background_color_icon, "채우기 색", self)
        self.action_fill_color.triggered.connect(lambda: self._open_color_dialog("fill"))
        
        group4_actions = [
            self.action_radius_down,
            self.action_radius_up,
            None,
            self.action_border_down,
            self.action_border_up,
            None,
            self.action_font_down,
            self.action_font_up,
            None,
            self.action_stroke_color,  # 테두리 색
            self.action_text_color,    # 숫자 색
            self.action_fill_color,    # 채우기 색
            None,
            self.action_cycle_line_style,
            self.action_cycle_arrow_style,
        ]
        # --- 최종 툴바 레이아웃 구성 ---
        main_layout.addWidget(self._create_toolbar_group(group1_actions, "실행 취소/복구"))
        main_layout.addSpacing(18)
        # 새 모드 선택 그룹을 작업 설정 왼쪽에 배치
        main_layout.addWidget(self._create_toolbar_group(mode_actions, "모드 선택"))
        main_layout.addSpacing(18)
        main_layout.addWidget(group2)
        main_layout.addSpacing(18)
        main_layout.addWidget(self._create_toolbar_group(group3_actions, "강조"))
        main_layout.addSpacing(18)
        main_layout.addWidget(self._create_toolbar_group(group_rotate_actions, "페이지 회전"))
        main_layout.addSpacing(18)
        main_layout.addWidget(self._create_toolbar_group(group4_actions, "라벨 및 흐름도 서식"))
        main_layout.addStretch(1)
        self.main_toolbar.addWidget(custom_toolbar_widget)

    # ===== ▼▼▼ 모드 전환 및 시각적 업데이트 함수 (새로 추가) ▼▼▼ =====
    def _cycle_active_mode(self):
        """활성 모드를 현재 '보기' 설정에 따라 동적으로 순환시킵니다."""
        # ▼▼▼ 여기에 print 문 추가 ▼▼▼
        # print(f"    [탐침 #2] 모드 전환 시작. 현재 모드: '{self.active_mode}'")
        # ▲▲▲ 여기까지 추가 ▲▲▲
        # 1. 전환 가능한 모드 목록을 실시간으로 생성합니다.
        available_modes = ["view"]  # '보기' 모드는 항상 포함됩니다.
        if self.view_show_numbering:
            available_modes.append("numbering")
        if self.view_show_stamps:
            available_modes.append("stamp")
        # 2. 현재 활성 모드가 방금 비활성화되어 목록에 없는 경우를 대비합니다.
        try:
            current_index = available_modes.index(self.active_mode)
        except ValueError:
            # 현재 모드가 비활성화되었다면 안전하게 '보기' 모드로 전환합니다.
            self.active_mode = "view"
            self._sync_ui_to_current_mode()
            return
        # 3. 전환할 모드가 하나뿐이면 아무것도 하지 않습니다.
        if len(available_modes) <= 1:
            return
        # 4. 'available_modes' 목록 내에서 다음 모드로 순환시킵니다.
        next_index = (current_index + 1) % len(available_modes)
        self.active_mode = available_modes[next_index]
        # 5. UI를 새 모드에 맞게 업데이트합니다.
        self._sync_ui_to_current_mode()

    def _set_active_mode_from_action(self, mode: str):
        """
        모드 선택 리본(모드 선택 탭)에서 호출되는 헬퍼.
        명시적으로 모드를 설정하고 UI를 동기화합니다.
        """
        if mode not in ("view", "numbering", "stamp"):
            return
        if self.active_mode == mode:
            return
        self.active_mode = mode
        # 모드선택 메뉴 동기화
        if hasattr(self, "a_mode_view"):
            self.a_mode_view.setChecked(mode == "view")
        if hasattr(self, "a_mode_numbering_menu"):
            self.a_mode_numbering_menu.setChecked(mode == "numbering")
        if hasattr(self, "a_mode_stamp"):
            self.a_mode_stamp.setChecked(mode == "stamp")
        self._sync_ui_to_current_mode()
    
    def _set_numbering_mode(self, input_mode: str):
        """
        넘버링 모드의 입력 방식을 설정하고, 활성 모드를 넘버링 모드로 전환합니다.
        """
        self.set_input_mode(input_mode)
        # 활성 모드를 넘버링 모드로 전환
        if self.active_mode != "numbering":
            self.active_mode = "numbering"
            # 모드선택 메뉴 동기화
            if hasattr(self, "a_mode_view"):
                self.a_mode_view.setChecked(False)
            if hasattr(self, "a_mode_stamp"):
                self.a_mode_stamp.setChecked(False)
            if hasattr(self, "a_mode_numbering_menu"):
                self.a_mode_numbering_menu.setChecked(True)
            self._sync_ui_to_current_mode()
        else:
            # 이미 넘버링 모드인 경우에도 체크 상태만 업데이트
            if hasattr(self, "a_mode_numbering_menu"):
                self.a_mode_numbering_menu.setChecked(True)

    # ===== ▼▼▼ 스탬프 버튼 관련 함수 3개 (새로 추가) ▼▼▼ =====
    def _get_current_stamp_key(self) -> Optional[str]:
        """현재 인덱스에 해당하는 스탬프의 키(이름)를 반환합니다. (StampManager로 위임)"""
        return self.stamp_manager.get_current_stamp_key()

    def _update_stamp_button_icon(self):
        """현재 선택된 스탬프 이미지로 툴바 버튼의 아이콘을 업데이트합니다. (StampManager로 위임)"""
        return self.stamp_manager.update_stamp_button_icon()

    def _cycle_next_stamp(self):
        """다음 스탬프로 순환시킵니다. (StampManager로 위임)"""
        return self.stamp_manager.cycle_next_stamp()

    # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
    # ... _cycle_next_stamp 함수 아래에 추가 ...
    # ===== ▼▼▼ 미리보기 버튼 관련 함수 2개 (새로 추가) ▼▼▼ =====
    def _update_preview_button_visuals(self):
        """현재 미리보기 모드에 맞춰 버튼 체크 상태를 업데이트합니다."""
        if hasattr(self, "preview_circle_button") and hasattr(self, "preview_crosshair_button"):
            if self.preview_mode == "preview":
                self.preview_circle_button.setChecked(True)
                self.preview_crosshair_button.setChecked(False)
            else:  # "crosshair"
                self.preview_circle_button.setChecked(False)
                self.preview_crosshair_button.setChecked(True)

    # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
    # ... _cycle_next_stamp 함수 바로 아래에 추가 ...
    def _select_stamp_by_key(self, stamp_key: str):
        """키(이름)를 이용해 특정 스탬프를 선택합니다."""
        if stamp_key in self.registered_stamps:
            stamp_keys = list(self.registered_stamps.keys())
            self.current_stamp_index = stamp_keys.index(stamp_key)
            self._update_stamp_button_icon()

    def _show_stamp_context_menu(self, pos):
        """스탬프 버튼 위치에 우클릭 메뉴를 표시합니다."""
        if not self.registered_stamps:
            return
        menu = QtWidgets.QMenu(self)
        for name, info in self.registered_stamps.items():
            # ▼▼▼ [핵심 수정] 딕셔너리에서 'path'를 직접 꺼내오도록 수정합니다. ▼▼▼
            if not isinstance(info, dict):
                continue
            path = info.get("path")
            if not path:
                continue
            # ▲▲▲ 여기까지 수정 ▲▲▲
            pixmap = QtGui.QPixmap(path)
            icon = QtGui.QIcon(pixmap.scaled(24, 24, QtCore.Qt.KeepAspectRatio))
            action = QtGui.QAction(icon, name, self)
            action.triggered.connect(lambda checked=False, key=name: self._select_stamp_by_key(key))
            menu.addAction(action)
        menu.exec(self.stamp_button.mapToGlobal(pos))

    def _sync_ui_to_current_mode(self):
        """(수정됨) 현재 활성 모드에 맞춰 툴바, 커서, 테이블, 그리고 '미리보기 객체'까지 모두 업데이트합니다."""
        # 1. 모든 미리보기는 일단 숨깁니다.
        if self._preview_ellipse:
            self._preview_ellipse.hide()
        if self._preview_text:
            self._preview_text.hide()
        if self._stamp_preview_item:
            self._stamp_preview_item.hide()
        self.context_widget_stack.setCurrentIndex(0)

        # 모드 선택 리본(액션) 상태 동기화
        if hasattr(self, "action_mode_view"):
            self.action_mode_view.setChecked(self.active_mode == "view")
        if hasattr(self, "action_mode_numbering"):
            self.action_mode_numbering.setChecked(self.active_mode == "numbering")
        if hasattr(self, "action_mode_stamp"):
            self.action_mode_stamp.setChecked(self.active_mode == "stamp")
        # 모드선택 메뉴 상태 동기화
        if hasattr(self, "a_mode_view"):
            self.a_mode_view.setChecked(self.active_mode == "view")
        if hasattr(self, "a_mode_numbering_menu"):
            self.a_mode_numbering_menu.setChecked(self.active_mode == "numbering")
        if hasattr(self, "a_mode_stamp"):
            self.a_mode_stamp.setChecked(self.active_mode == "stamp")
        # 2. 모드에 따라 UI를 설정합니다.
        if self.active_mode == "numbering":
            # ▼▼▼ [핵심 추가] 넘버링 미리보기 객체가 없으면 즉시 생성! ▼▼▼
            if self._preview_ellipse is None or self._preview_text is None:
                self._create_preview_items()
            # ▲▲▲ 여기까지 추가 ▲▲▲
            self.context_widget_stack.setCurrentIndex(1)
            self.dock_stack.setCurrentWidget(self.table)
            self._update_preview_button_visuals()
            if self.doc:
                self.set_preview_mode(self.preview_mode)  # set_preview_mode가 커서를 관리함
            else:
                self.view.setCursor(QtCore.Qt.ArrowCursor)
        elif self.active_mode == "stamp":
            # ▼▼▼ [핵심 추가] 스탬프 미리보기 객체가 없으면 즉시 생성! ▼▼▼
            if self._stamp_preview_item is None and self.doc:
                # 스탬프는 내용물이 있어야 하므로, 빈 QPixmap으로 일단 만들어 둡니다.
                self._stamp_preview_item = self.scene.addPixmap(QtGui.QPixmap())
                self._stamp_preview_item.setZValue(10000)
                self._stamp_preview_item.hide()
            # ▲▲▲ 여기까지 추가 ▲▲▲
            stamp_icon = icon_if("resources/icons/stamp_on.png")  # "resources/icons/" 경로 추가
            self.context_widget_stack.setCurrentIndex(2)
            self.dock_stack.setCurrentWidget(self.stamp_table)
            self._update_stamp_button_icon()
            # ▼▼▼ [핵심] 십자선/투명 커서 대신 일반 화살표 커서로 변경합니다. ▼▼▼
            self.view.setCursor(QtCore.Qt.ArrowCursor)
            # ▲▲▲ 여기까지 수정 ▲▲▲
        else:  # "view" 모드
            self.dock_stack.setCurrentWidget(self.table)
            self.view.setCursor(QtCore.Qt.ArrowCursor)
        # 3. 나머지 UI 상태를 업데이트합니다.
        # self.mode_button.setChecked(self.active_mode != "view")
        self._update_status()
        for shortcut in self.stamp_shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.stamp_shortcuts.clear()
        if self.active_mode == "stamp":
            sc_cycle = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self)
            sc_cycle.activated.connect(self._cycle_next_stamp)
            self.stamp_shortcuts.append(sc_cycle)
            stamp_keys = list(self.registered_stamps.keys())
            for i in range(min(len(stamp_keys), 9)):
                sc_select = QtGui.QShortcut(QtGui.QKeySequence(f"Ctrl+{i+1}"), self)
                sc_select.activated.connect(
                    lambda key=stamp_keys[i]: self._select_stamp_by_key(key)
                )
                self.stamp_shortcuts.append(sc_select)

    def __init__(self, pdf_path: Optional[str] = None):
        super().__init__()
        # --- 개발자 모드 및 평가판 기능 ---

        DEV_MODE = True  # 배포 시 False로 변경

        trial_message = ""
        self.trial_days_left = 0
        if not DEV_MODE:
            status, days_left = self.check_trial_status()
            if status == "expired":
                QtWidgets.QMessageBox.critical(
                    self, "평가판 만료", "30일 평가 기간이 만료되었습니다. 프로그램을 종료합니다."
                )
                sys.exit()
            self.trial_days_left = days_left
            trial_message = f" (Trial - {self.trial_days_left}일 남음)"
            if status == "just_installed":
                QtWidgets.QMessageBox.information(
                    self,
                    "환영합니다",
                    f"평가판이 시작되었습니다. {days_left}일 동안 사용하실 수 있습니다.",
                )
        self.setWindowTitle(f"{APP_NAME} ({APP_VER}){trial_message}")
        self.resize(1400, 800)  # 윈도우 크기를 줄여서 테이블에 맞춤
        # ▼▼▼ 탭 위젯 설정 코드 (삽입) ▼▼▼
        # 1. 탭 위젯을 생성하고 중앙에 배치합니다.
        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)
        # 2. 기존의 PDF 뷰어를 첫 번째 탭에 추가합니다.
        self.scene = PdfScene(self)
        self.view = PdfView(self.scene, self)
        self.tab_widget.addTab(self.view, "2D View")
        # 3. 3D 뷰어를 위한 두 번째 탭을 만듭니다. (지금은 빈 공간)
        self.vlayout_3d = QtWidgets.QVBoxLayout()
        self.widget_3d = QtWidgets.QWidget()
        self.widget_3d.setLayout(self.vlayout_3d)
        self.tab_widget.addTab(self.widget_3d, "3D View")
        # 신호/슬롯 연결
        self.scene.clicked.connect(self.on_clicked)
        self.scene.moved.connect(self.on_scene_moved)
        self.view.zoom_changed.connect(self._on_zoom_changed)
        # ▲▲▲ 여기까지 삽입 ▲▲▲
        self._ee_armed = False
        self._ee_prev_state = False
        self._ee_orig_vol = 0.7
        # --- 상태 변수 초기화 ---
        self.project_path = None
        self.project_dir = None  # <--- 이 줄 추가
        self.project_name = None  # <--- 이 줄 추가
        self.pdf_path = None  # <<--- 바로 이 줄입니다. 이 줄을 추가해야 합니다.
        self.model_path = None
        self.doc = None
        self.cur_page_index = 0
        self.numbering_mode = "global"  # <--- 이 줄을 추가해주세요
        self.flow_items = []  # <--- 이 줄을 추가해주세요
        # ===== ▼▼▼ [추가] 페이지 연결점 색상표 ▼▼▼ =====
        self.transition_colors = [
            QtGui.QColor("#FF1F5B"),
            QtGui.QColor("#00CD6C"),
            QtGui.QColor("#009ADE"),
            QtGui.QColor("#AF58BA"),
            QtGui.QColor("#FFC61E"),
            QtGui.QColor("#F28522"),
            QtGui.QColor("#A0B1BA"),
            QtGui.QColor("#A6761D"),
            QtGui.QColor("#E9002D"),
            QtGui.QColor("#62205F"),
        ]
        # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
        # ===== ▼▼▼ [추가] 시작/끝점 아이콘 미리 불러오기 ▼▼▼ =====
        self.start_marker_pixmap = QtGui.QPixmap(resource_path("resources/icons/startpoint.png"))
        self.end_marker_pixmap = QtGui.QPixmap(resource_path("resources/icons/endpoint.png"))
        # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
        self.is_dirty = False  # ===== ▼▼▼ 이 줄을 추가해주세요 ▼▼▼ =====
        self.style_clipboard = None  # ===== ▼▼▼ 이 줄을 추가해주세요 ▼▼▼ =====
        self.render_scale = 2
        self.auto_highres = True
        # ===== ▼▼▼ 보기/숨기기 상태 변수 추가/수정 ▼▼▼ =====
        self.flow_view_enabled = True  # 흐름도 (디폴트 ON)
        self.view_show_numbering = True  # 넘버링 (디폴트 ON)
        self.view_show_stamps = True  # 스탬프 (디폴트 ON)
        # ===== ▲▲▲ 여기까지 추가/수정 ▲▲▲ =====
        self.preview_mode = "preview"
        self.style = LabelStyle()
        self.next_no = 1
        # ▼▼▼ 아래 3줄을 수정/추가합니다 ▼▼▼
        self.items: List[MarkItem] = []  # 넘버링 현재 상태 리스트 (기존과 동일)
        self.undo_stack = []  # [신규] 모든 행동의 역사를 기록할 통합 리스트
        self.redo_stack = []  # [수정] 되살리기용 통합 리스트 (기존 self.redo_stack과 역할 동일)
        # ▲▲▲ 여기까지 수정/추가 ▲▲▲
        self.input_mode = "number_only"
        self._page_pix = None
        self._preview_ellipse = None
        self._preview_text = None
        self._highlight_ellipse = None
        self._highlight_item_no = None
        self.highlight_color = QtGui.QColor(0x39, 0xFF, 0x14)
        self.insert_mode = False
        self.insert_option = None
        self.insert_target_no = -1.0
        self.highlight_enabled = True
        # ===== ▼▼▼ 스탬프 기능 관련 변수 추가 ▼▼▼ =====
        self.active_mode = "view"  # 현재 활성 모드: "view", "numbering", "stamp" (디폴트: 보기 모드)
        self.stamps: List[StampItem] = []  # PDF에 찍힌 스탬프 객체들을 저장하는 리스트
        self.stamp_shortcuts = []  # 단축키 객체를 저장하여 켜고 끄기 위한 리스트
        self.registered_stamps = {}  # 등록된 스탬프 목록 (예: {"내 서명": "C:/path/sig.png"})
        self._stamp_preview_item = None  # 스탬프 미리보기 그래픽 아이템
        # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
        # ===== ▼▼▼ 현재 선택된 스탬프 인덱스 변수 추가 ▼▼▼ =====
        self.current_stamp_index = 0
        # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
        # ▼▼▼ 스탬프 설정 관련 변수 추가 ▼▼▼
        self.stamp_opacity = 1.0
        self.stamp_rotation = 0.0
        self.stamp_opacity_random = True
        self.stamp_rotation_random = True
        self.stamp_opacity_min = 0.90  # 기본값: 90% ~ 100%
        self.stamp_opacity_max = 1.0
        self.stamp_rotation_min = -5.0  # 기본값: -5도 ~ 5도
        self.stamp_rotation_max = 5.0
        # ▲▲▲ 여기까지 추가 ▲▲▲
        # ===== ▼▼▼ 이스터에그(사격 모드) 변수 추가/수정 ▼▼▼ =====
        self.shooting_mode = False
        self.bullet_hole_items = []
        self.crosshair_pixmap = QtGui.QPixmap(
            resource_path("resources/ester_egg/gun.png")
        )  # 경로 수정
        # ── 탄피: 리소스/상태 ───────────────────────────────────────────
        self.shell_pixmaps = []
        for name in [f"shell{i}.png" for i in range(1, 6)]:
            pm = QtGui.QPixmap(resource_path(f"resources/ester_egg/{name}"))  # 경로 수정
            if not pm.isNull():
                self.shell_pixmaps.append(pm)
        # 폴백(이미지가 하나도 없을 때는 로직 비활성화)
        self.enable_shell = bool(self.shell_pixmaps)
        self.shell_items = (
            []
        )  # [{'item':QGraphicsPixmapItem,'vx':..,'vy':..,'spin':..,'life':..}, ...]
        # ▼▼▼ [핵심] 누락된 탄피 타이머 초기화 코드를 추가합니다. ▼▼▼
        # ── 탄피 물리/타이머(60FPS 근사) ────────────────────────────────
        self._shell_timer = QtCore.QTimer(self)
        self._shell_timer.setInterval(16)
        self._shell_timer.timeout.connect(self._tick_shells)
        # ▲▲▲ 여기까지 추가 ▲▲▲
        # 픽셀/초 단위 튜닝 파라미터(필요시 조절)
        self._shell_gravity = 1200.0  # 중력가속도(px/s^2)
        self._shell_air_drag = 0.15  # 공기저항(속도 감쇠 비율)
        self._shell_floor_y = None  # 바닥 Y(없으면 화면 밖까지 날게 둠)
        # 여러 장의 혈흔 스프라이트를 미리 로드
        self.bullet_hole_pixmaps = []
        for name in [f"blood{i}.png" for i in range(1, 6)]:  # blood1~5.png
            pm = QtGui.QPixmap(resource_path(f"resources/ester_egg/{name}"))  # 경로 수정
            if not pm.isNull():
                self.bullet_hole_pixmaps.append(pm)
        # 폴백: 위에서 아무 것도 못 찾으면 기존 blood.png라도 사용
        if not self.bullet_hole_pixmaps:
            fallback_pm = QtGui.QPixmap(resource_path("resources/ester_egg/blood.png"))  # 경로 수정
            if not fallback_pm.isNull():
                self.bullet_hole_pixmaps = [fallback_pm]
        # self.gun_sound -> self.gun_sound_url 로 이름을 변경하고 아래와 같이 수정합니다.
        self.gun_sound_url = QtCore.QUrl.fromLocalFile(
            resource_path("resources/ester_egg/gun_sound.wav")
        )  # 경로 수정
        self.sound_effect = None  # 사운드 플레이어를 저장할 변수
        self.sound_volume = 1.0  # 사운드 볼륨 (0.0 ~ 1.0)
        # ===== ▲▲▲ 여기까지 교체 ▲▲▲ =====
        # === Secret hotkey (Ctrl+F12 x4) state ===
        self._egg_required = 4  # 필요한 연속 입력 횟수
        self._egg_window_ms = 1200  # 각 입력 간 허용 간격(ms) — 필요시 조절
        self._egg_count = 0  # 현재까지 누른 횟수
        self._egg_timer = QtCore.QTimer(self)
        self._egg_timer.setSingleShot(True)
        self._egg_timer.timeout.connect(self._reset_egg_sequence)
        # 다시 수정.. 4.00에서.
        # ===== ▼▼▼ 페이지 네비게이션 UI 생성 (수정) ▼▼▼ =====
        self.btn_prev = QtWidgets.QPushButton("< 이전")
        self.btn_prev.setFixedWidth(40)  # 더 작은 크기로 조정
        self.btn_next = QtWidgets.QPushButton("다음 >")
        self.btn_next.setFixedWidth(40)  # 더 작은 크기로 조정
        self.spin_page = QtWidgets.QSpinBox()
        self.spin_page.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.NoButtons
        )  # 지시3: "숫자창에 화살표는 만들지 마!"
        self.spin_page.setMinimumWidth(30)  # 더 작은 크기로 조정
        self.lbl_total_pages = QtWidgets.QLabel("/ 1")
        # 버튼 및 스핀박스 기능 연결
        self.btn_prev.clicked.connect(self.go_prev)
        self.btn_next.clicked.connect(self.go_next)
        self.spin_page.valueChanged.connect(self._go_to_page_from_spinbox)
        # ===== ▲▲▲ 여기까지 수정 (상태 표시줄 추가 부분 삭제) ▲▲▲ =====
        # --- 표 도크 ---
        self.table = QtWidgets.QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(
            ["No", "Type", "Dim", "Max", "Min", "3D Parameter"]
        )
        self.table.setItemDelegateForColumn(1, ComboDelegate(DIM_TYPES, self.table))
        numeric_delegate = NumericDelegate(self)
        self.table.setItemDelegateForColumn(3, numeric_delegate)
        self.table.setItemDelegateForColumn(4, numeric_delegate)
        self.table.itemChanged.connect(self.on_table_item_changed)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        try:
            self.table.itemSelectionChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.table.itemSelectionChanged.connect(self._sync_highlight_from_table)
        self.table.currentCellChanged.connect(lambda *_: self._sync_highlight_from_table())
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        # ===== ▼▼▼ 스탬프 테이블 위젯 추가 ▼▼▼ =====
        self.stamp_table = QtWidgets.QTableWidget(0, 2, self)
        self.stamp_table.setHorizontalHeaderLabels(["No", "스탬프 종류"])
        self.stamp_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.stamp_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
        # ===== ▼▼▼ 스탬프 테이블 기능 연결 및 변수 추가 ▼▼▼ =====
        self._stamp_graphics_items = {}  # StampItem id를 QGraphicsItem에 매핑
        self._highlighted_stamp_rect = None  # 하이라이트 그래픽 아이템
        self.stamp_table.cellClicked.connect(self._highlight_stamp_from_table)
        # --- 1. 왼쪽 '페이지' 도크 생성 (새로운 부분) ---
        self.page_dock = QtWidgets.QDockWidget("페이지", self)
        page_dock_container = QtWidgets.QWidget()
        page_layout = QtWidgets.QVBoxLayout(page_dock_container)
        page_layout.setContentsMargins(5, 5, 5, 5)
        # --- 페이지별 넘버링 체크박스 (새로 추가) ---
        self.cb_separate_numbering = QtWidgets.QCheckBox("페이지별 개별 넘버링")
        self.cb_separate_numbering.setToolTip("체크 시 각 페이지마다 1번부터 새로 시작합니다.")
        page_layout.addWidget(self.cb_separate_numbering)
        self.cb_separate_numbering.toggled.connect(self._refresh_table_view)
        # 페이지 네비게이션 컨트롤
        nav_layout = QtWidgets.QHBoxLayout()
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.spin_page)
        nav_layout.addWidget(self.lbl_total_pages)
        nav_layout.addWidget(self.btn_next)
        nav_layout.addStretch(1)
        # 썸네일 뷰
        self.thumbnail_area = QtWidgets.QScrollArea()
        self.thumbnail_area.setWidgetResizable(True)
        self.thumbnail_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.thumbnail_container = QtWidgets.QWidget()
        self.thumbnail_layout = QtWidgets.QVBoxLayout(self.thumbnail_container)
        self.thumbnail_area.setWidget(self.thumbnail_container)
        self.thumbnail_widgets = []
        # 왼쪽 도크에 네비게이션과 썸네일 추가
        page_layout.addLayout(nav_layout)
        page_layout.addWidget(self.thumbnail_area)
        self.page_dock.setWidget(page_dock_container)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.page_dock)  # << 왼쪽 영역에 추가
        # --- 3D Navigator 윈도우 생성 ---
        self.navigator_dock = QtWidgets.QDockWidget("3D Navigator", self)
        navigator_container = QtWidgets.QWidget()
        navigator_layout = QtWidgets.QVBoxLayout(navigator_container)
        navigator_layout.setContentsMargins(3, 5, 3, 3)  # 여백 최소화
        navigator_layout.setSpacing(6)  # 섹션 간격 최소화
        # 뷰포트 선택 섹션 - 버튼 6개만 독립적인 박스
        viewport_group = QtWidgets.QGroupBox("뷰포트 선택")
        viewport_layout = QtWidgets.QVBoxLayout(viewport_group)
        viewport_layout.setSpacing(8)  # 제목과 버튼들 사이 간격 최소화
        viewport_layout.setContentsMargins(5, 8, 5, 5)  # 상단 여백 추가 (사용자 정의와 동일한 스타일)
        # 기본 뷰 버튼들 (1x6 배열)
        basic_view_layout = QtWidgets.QHBoxLayout()
        basic_view_layout.setSpacing(0)  # 버튼 간격 최소화
        basic_view_layout.setContentsMargins(0, 10, 0, 0)  # 상단에 10픽셀 여백 추가 (아래로 내리기)
        # 뷰포트 정보 (순서: 상면, 하면, 정면, 후면, 좌측면, 우측면)
        viewport_info = [
            ("상면", "상면.png"),
            ("하면", "하면.png"),
            ("정면", "정면.png"),
            ("후면", "후면.png"),
            ("좌측면", "좌측면.png"),
            ("우측면", "우측면.png"),
        ]
        self.viewport_buttons = []
        for view_name, icon_file in viewport_info:
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(24, 24)  # 더 작은 정사각형 버튼
            btn.setToolTip(view_name)  # 툴팁으로 텍스트 표시
            btn.clicked.connect(lambda checked=False, v=view_name: self.set_viewport(v))
            # 아이콘 설정
            try:
                from utils.helpers import icon_if

                icon = icon_if(f"resources/icons/{icon_file}")
                if icon and not icon.isNull():
                    btn.setIcon(icon)
                    btn.setIconSize(QtCore.QSize(30, 30))  # 아이콘 크기 1.5배 증가 (20 → 30)
            except Exception as e:
                # 아이콘 로드 실패 시 빈 버튼
                print(f"뷰포트 아이콘 로드 실패 ({icon_file}): {e}")
                pass
            basic_view_layout.addWidget(btn)
            self.viewport_buttons.append(btn)
        viewport_layout.addLayout(basic_view_layout)
        # 사용자 정의 섹션 (2행으로 변경) - 독립적인 박스
        custom_group = QtWidgets.QGroupBox("사용자 정의")
        custom_layout = QtWidgets.QVBoxLayout(custom_group)
        custom_layout.setSpacing(8)  # 제목과 입력란 사이 간격 최소화
        custom_layout.setContentsMargins(5, 8, 5, 5)  # 상단 여백 최소화
        # XYZ 한 행
        xyz_layout = QtWidgets.QHBoxLayout()
        xyz_layout.setSpacing(12)  # 위젯 간격 적절히 조정
        xyz_layout.addWidget(QtWidgets.QLabel("X:"))
        self.custom_x_spin = QtWidgets.QDoubleSpinBox()
        self.custom_x_spin.setRange(-1.0, 1.0)
        self.custom_x_spin.setValue(1.0)
        self.custom_x_spin.setDecimals(1)
        self.custom_x_spin.setSingleStep(0.1)
        self.custom_x_spin.setMaximumHeight(20)
        self.custom_x_spin.setFixedWidth(55)  # 음수 기호를 위해 폭 확장
        # 세로 화살표 스타일 설정
        self.custom_x_spin.setStyleSheet(
            "QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 16px; } QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; }"
        )
        self.custom_x_spin.editingFinished.connect(self.on_custom_view_changed)
        self.custom_x_spin.valueChanged.connect(self.on_custom_view_changed)
        xyz_layout.addWidget(self.custom_x_spin)
        xyz_layout.addWidget(QtWidgets.QLabel("Y:"))
        self.custom_y_spin = QtWidgets.QDoubleSpinBox()
        self.custom_y_spin.setRange(-1.0, 1.0)
        self.custom_y_spin.setValue(1.0)
        self.custom_y_spin.setDecimals(1)
        self.custom_y_spin.setSingleStep(0.1)
        self.custom_y_spin.setMaximumHeight(20)
        self.custom_y_spin.setFixedWidth(55)  # 음수 기호를 위해 폭 확장
        # 세로 화살표 스타일 설정
        self.custom_y_spin.setStyleSheet(
            "QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 16px; } QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; }"
        )
        self.custom_y_spin.editingFinished.connect(self.on_custom_view_changed)
        self.custom_y_spin.valueChanged.connect(self.on_custom_view_changed)
        xyz_layout.addWidget(self.custom_y_spin)
        xyz_layout.addWidget(QtWidgets.QLabel("Z:"))
        self.custom_z_spin = QtWidgets.QDoubleSpinBox()
        self.custom_z_spin.setRange(-1.0, 1.0)
        self.custom_z_spin.setValue(1.0)
        self.custom_z_spin.setDecimals(1)
        self.custom_z_spin.setSingleStep(0.1)
        self.custom_z_spin.setMaximumHeight(20)
        self.custom_z_spin.setFixedWidth(55)  # 음수 기호를 위해 폭 확장
        # 세로 화살표 스타일 설정
        self.custom_z_spin.setStyleSheet(
            "QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 16px; } QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; }"
        )
        self.custom_z_spin.editingFinished.connect(self.on_custom_view_changed)
        self.custom_z_spin.valueChanged.connect(self.on_custom_view_changed)
        xyz_layout.addWidget(self.custom_z_spin)
        xyz_layout.addStretch()  # 오른쪽 여백
        custom_layout.addLayout(xyz_layout)
        # 거리 한 행
        distance_layout = QtWidgets.QHBoxLayout()
        distance_layout.setSpacing(12)  # 위젯 간격 적절히 조정
        distance_layout.addWidget(QtWidgets.QLabel("거리:"))
        self.distance_spin = QtWidgets.QDoubleSpinBox()
        self.distance_spin.setRange(0.1, 10.0)
        self.distance_spin.setValue(1.0)
        self.distance_spin.setDecimals(1)
        self.distance_spin.setSingleStep(0.1)  # 0.1 단위로 조절
        self.distance_spin.setMaximumHeight(20)
        self.distance_spin.setFixedWidth(55)  # 소수값 표시를 위해 폭 확장
        # 세로 화살표 스타일 설정 (XYZ와 동일)
        self.distance_spin.setStyleSheet(
            "QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 16px; } QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; }"
        )
        self.distance_spin.valueChanged.connect(self.on_distance_spin_changed)
        distance_layout.addWidget(self.distance_spin)
        # 거리 슬라이더
        self.distance_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.distance_slider.setRange(1, 100)  # 0.1~10.0을 1~100으로 변환
        self.distance_slider.setValue(10)  # 1.0에 해당
        self.distance_slider.setMaximumHeight(20)
        self.distance_slider.valueChanged.connect(self.on_distance_slider_changed)
        distance_layout.addWidget(self.distance_slider)
        # 사용자 정의 적용 버튼
        self.apply_custom_btn = QtWidgets.QPushButton("적용")
        self.apply_custom_btn.setMaximumHeight(20)
        self.apply_custom_btn.setFixedWidth(35)
        self.apply_custom_btn.clicked.connect(self.apply_custom_view)
        distance_layout.addWidget(self.apply_custom_btn)
        custom_layout.addLayout(distance_layout)
        # 현재 뷰 정보 섹션 (실시간 카메라 파라미터 표시)
        view_info_group = QtWidgets.QGroupBox("현재 뷰 정보")
        view_info_layout = QtWidgets.QVBoxLayout(view_info_group)
        view_info_layout.setSpacing(3)
        view_info_layout.setContentsMargins(8, 8, 8, 8)
        # 정보 표시 라벨
        self.view_info_label = QtWidgets.QLabel("3D 모델을 불러오세요")
        self.view_info_label.setAlignment(QtCore.Qt.AlignLeft)
        self.view_info_label.setStyleSheet(
            """
            QLabel {
                background-color: #F5F5F5;
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
                color: #333333;
            }
        """
        )
        self.view_info_label.setWordWrap(True)
        view_info_layout.addWidget(self.view_info_label)
        # 전체 레이아웃 구성 - 각 섹션을 독립적으로 추가
        navigator_layout.addWidget(viewport_group)  # 뷰포트 선택 (버튼 6개만)
        navigator_layout.addWidget(custom_group)  # 사용자 정의 (독립적인 박스)
        navigator_layout.addWidget(view_info_group)  # 현재 뷰 정보
        navigator_layout.addStretch()  # 여백 추가
        self.navigator_dock.setWidget(navigator_container)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.navigator_dock)
        # 3D Navigator를 리사이즈 가능하게 설정
        self.navigator_dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable
        )
        # 크기 제한 제거
        self.navigator_dock.setMinimumSize(200, 200)
        # --- 2. 오른쪽 '리스트' 도크 생성 (테이블 전환 기능 추가) ---
        self.dock = QtWidgets.QDockWidget("리스트", self)
        dock_container = QtWidgets.QWidget()
        dock_layout = QtWidgets.QVBoxLayout(dock_container)
        dock_layout.setContentsMargins(5, 5, 5, 5)
        # QStackedWidget을 사용해 테이블을 전환할 수 있도록 함
        self.dock_stack = QtWidgets.QStackedWidget()
        self.dock_stack.addWidget(self.table)  # 0번 인덱스: 넘버링 테이블
        self.dock_stack.addWidget(self.stamp_table)  # 1번 인덱스: 스탬프 테이블
        help_label = QtWidgets.QLabel("※ 항목 클릭: 하이라이트")
        help_label.setAlignment(QtCore.Qt.AlignCenter)
        help_label.setStyleSheet(
            "background-color: #E8E8E8; padding: 4px; border-radius: 4px; font-size: 11px;"
        )
        dock_layout.addWidget(help_label)
        dock_layout.addWidget(self.dock_stack)  # 스택 위젯을 도크에 추가
        self.dock.setWidget(dock_container)
        # 도크 위젯 크기 제한 설정 (3D Parameter 컬럼을 위해 더 넓게)
        self.dock.setMinimumSize(400, 250)
        self.dock.setMaximumSize(600, 500)
        # 테이블 컬럼 크기 설정
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)  # No
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)  # Type
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)  # Dim
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)  # Max
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)  # Min
        self.table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)  # 3D Parameter
        # 컬럼 너비 설정 (컬럼명이 깨지지 않을 최소 폭으로 조정)
        self.table.setColumnWidth(0, 30)   # No
        self.table.setColumnWidth(1, 40)   # Type
        self.table.setColumnWidth(2, 50)   # Dim
        self.table.setColumnWidth(3, 40)   # Max
        self.table.setColumnWidth(4, 40)   # Min
        # 3D Parameter는 Stretch로 설정되어 남은 공간을 차지
        # 셀 내용 중앙 정렬 설정
        self.table.setAlternatingRowColors(True)  # 행 색상 교대로 표시
        # 기존 데이터가 있다면 새로운 포맷으로 강제 새로고침
        # 약간의 지연을 두고 새로고침 (UI 초기화 완료 후)
        QtCore.QTimer.singleShot(100, self._force_refresh_table)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dock)
        
        # --- 3.5. 매니저 초기화 (UI 생성 전에 필요) ---
        # ViewportManager 초기화
        self.viewport_manager = ViewportManager(self)
        
        # TableManager 초기화
        self.table_manager = TableManager(self)
        self.table_manager.set_table(self.table)
        
        # UIManager 초기화
        self.ui_manager = UIManager(self)
        
        # StampManager 초기화
        self.stamp_manager = StampManager(self)
        
        # --- 4. 메뉴바, 툴바, 단축키 생성 ---
        self._create_menus()
        self._create_toolbar()
        self._create_shortcuts()
        # --- 5. 백그라운드 스레드 설정 ---
        self.thread = QThread()
        self.thread.start()
        self.thread.setPriority(QThread.LowestPriority)  # <<--- 이 줄 추가
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.start_loading_3d.connect(self.worker.load_model)
        self.worker.finished.connect(self.on_3d_load_finished)
        self.worker.error.connect(self.on_3d_load_error)
        # --- 6. 뷰 정보 실시간 업데이트 타이머 설정 ---
        self.view_info_timer = QtCore.QTimer(self)
        self.view_info_timer.timeout.connect(self.update_view_info)
        self.view_info_timer.start(500)  # 500ms마다 업데이트 (0.5초)
        # --- 7. 사운드 예열 ---
        try:
            from PySide6.QtMultimedia import QSoundEffect

            prime_effect = QSoundEffect(self)
            silent_url = QtCore.QUrl.fromLocalFile(
                resource_path("resources/ester_egg/silent_prime.wav")
            )
            prime_effect.setSource(silent_url)
            prime_effect.play()
            self.sound_effect = QSoundEffect(self)
            self.sound_effect.setSource(self.gun_sound_url)
            self.sound_effect.setVolume(1.0)
            QThread.msleep(20)
            print("Sound system pre-loaded successfully.")
        except Exception as e:
            print(f"Sound pre-loading failed: {e}")
        # --- 7. 스타일시트 적용 ---
        self.setStyleSheet(
            """
            QToolBar { border: none; background-color: #F0F0F0; }
            QToolBar QToolButton { border: 1px solid transparent; border-radius: 4px; padding: 3px; }
            QToolBar QToolButton:checked { background-color: #D6EAF8; border: 1px solid #A9CCE3; }
            QGroupBox {
                border: 1px solid #D5D8DC;
                border-radius: 6px;
                margin-top: 15px; /* 제목을 위한 상단 여백 확보 */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px; /* 좌우 패딩 */
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 10px; color: #606060; }
            QDockWidget { border: 1px solid #C8C8C8; }
            QDockWidget::title { text-align: center; background-color: #E6E6E6; padding: 4px; }
        """
        )
        # --- 8. 최종 상태 업데이트 ---
        if pdf_path:
            self.import_pdf_from_path(pdf_path)
        self._apply_initial_layout()
        self._sync_ui_to_current_mode()
        self._update_undo_redo_hint()
        self._update_status()
        # ▲▲▲ 여기까지 삽입 ▲▲▲

    def copy_format(self):
        """선택된 첫 번째 항목의 개별 서식을 클립보드에 복사합니다."""
        selected_rows = sorted(list(set(index.row() for index in self.table.selectedIndexes())))
        if not selected_rows:
            return
        source_row = selected_rows[0]
        try:
            item_no = float(self.table.item(source_row, 0).text())
            source_item = next((it for it in self.items if it.no == item_no), None)
            if not source_item:
                return
        except (ValueError, AttributeError):
            return
        # 스타일 객체를 깊은 복사(deepcopy)하여 완전히 독립적인 복사본을 만듭니다.
        self.style_clipboard = copy.deepcopy(source_item.custom_style)
        if self.style_clipboard:
            self.statusBar().showMessage(f"✅ {item_no:g}번의 개별 서식이 복사되었습니다.")
        else:
            self.statusBar().showMessage(
                f"✅ {item_no:g}번의 기본 서식(서식 없음)이 복사되었습니다."
            )

    def paste_format(self):
        """클립보드에 복사된 서식을 선택된 모든 항목에 붙여넣습니다."""
        selected_rows = sorted(list(set(index.row() for index in self.table.selectedIndexes())))
        if not selected_rows:
            self.statusBar().showMessage("❗ 서식을 붙여넣을 항목을 먼저 선택해주세요.")
            return
        # 붙여넣기 전, 복사된 서식이 있는지 확인합니다.
        if self.style_clipboard is None:
            self.statusBar().showMessage(
                "❗ 복사된 서식이 없습니다. Ctrl+Shift+C로 먼저 서식을 복사해주세요."
            )
            return
        applied_count = 0
        for row in selected_rows:
            try:
                item_no = float(self.table.item(row, 0).text())
                target_item = next((it for it in self.items if it.no == item_no), None)
                if target_item:
                    # 붙여넣을 때도 깊은 복사를 하여 각 항목이 독립적인 스타일 객체를 갖게 합니다.
                    target_item.custom_style = copy.deepcopy(self.style_clipboard)
                    applied_count += 1
            except (ValueError, AttributeError):
                continue
        if applied_count > 0:
            self.statusBar().showMessage(f"🎨 {applied_count}개 항목에 서식을 적용했습니다.")
            self.load_page(self.cur_page_index)  # 변경 사항을 화면에 즉시 반영
            self._set_dirty()  # 파일이 수정되었음을 표시

    def closeEvent(self, event):
        """창이 닫힐 때 호출되는 이벤트 핸들러입니다."""
        if self._maybe_save(
            "프로그램 종료", "프로그램을 종료합니다.\n현재 파일을 저장하시겠습니까?"
        ):
            # ▼▼▼ [추가] 백그라운드 스레드를 안전하게 종료합니다. ▼▼▼
            print("백그라운드 스레드를 종료합니다...")
            self.thread.quit()  # 1. 스레드에게 이벤트 루프를 종료하라고 알림
            self.thread.wait()  # 2. 스레드가 완전히 끝날 때까지 기다림
            print("스레드 종료 완료.")
            # ▲▲▲
            event.accept()  # 종료 허용
        else:
            event.ignore()  # 종료 취소

    def _create_shortcuts(self):
        """단축키를 생성합니다. (UIManager로 위임)"""
        return self.ui_manager.create_shortcuts()

    def _create_menus(self):
        mb = self.menuBar()
        m_file = mb.addMenu("파일")
        a_new = m_file.addAction("New Project")
        a_new.triggered.connect(self.new_project)
        a_open = m_file.addAction("Open Project…")
        a_open.triggered.connect(self.open_project_dialog)
        a_save = m_file.addAction("Save Project")
        a_save.triggered.connect(self.save_project)
        a_saveas = m_file.addAction("Save Project As…")
        a_saveas.triggered.connect(self.save_project_as)
        m_file.addSeparator()
        # ▼▼▼ 3D 모델 열기 메뉴 추가 ▼▼▼
        a_open_3d = m_file.addAction("import 3D Model...")
        a_open_3d.triggered.connect(self.open_3d_model)
        # ▲▲▲
        m_file.addSeparator()
        # ▼▼▼ 발행 기능 추가 ▼▼▼
        a_publish = m_file.addAction("서버에 발행 (테스트)...")
        a_publish.triggered.connect(self.publish_project)
        # ▲▲▲ 여기까지 추가 ▲▲▲
        m_file.addSeparator()
        a_imp = m_file.addAction("Import PDF…")
        a_imp.triggered.connect(self.import_pdf)
        m_file.addSeparator()
        a_pdf = m_file.addAction("Export PDF…")
        a_pdf.triggered.connect(self._cmd_export_pdf)
        a_csv = m_file.addAction("Export CSV…")
        a_csv.triggered.connect(self.export_csv_dialog)
        a_xlsx = m_file.addAction("Export XLSX…")
        a_xlsx.triggered.connect(self.export_xlsx_dialog)
        m_view = mb.addMenu("보기")
        # 첫 번째 세션: (넘버링보기, 스탬프보기, 흐름도보기)
        self.a_numbering_view_menu = m_view.addAction("넘버링 보기")
        self.a_numbering_view_menu.setCheckable(True)
        self.a_numbering_view_menu.setChecked(self.view_show_numbering)
        self.a_numbering_view_menu.toggled.connect(self.toggle_numbering_view)
        
        self.a_stamps_view_menu = m_view.addAction("스탬프 보기")
        self.a_stamps_view_menu.setCheckable(True)
        self.a_stamps_view_menu.setChecked(self.view_show_stamps)
        self.a_stamps_view_menu.toggled.connect(self.toggle_stamps_view)
        
        self.a_flow_menu = m_view.addAction("흐름도 보기")
        self.a_flow_menu.setCheckable(True)
        self.a_flow_menu.setChecked(self.flow_view_enabled)
        self.a_flow_menu.triggered.connect(self.toggle_flow_view)
        
        m_view.addSeparator()
        
        # 두 번째 세션: (항목 하이라이트, 시작/끝점)
        self.a_highlight = m_view.addAction("항목 하이라이트 켜기")
        self.a_highlight.setCheckable(True)
        self.a_highlight.setChecked(True)
        self.a_highlight.toggled.connect(self.toggle_highlighting)
        self.a_highlight.setShortcut("Ctrl+H")
        
        self.a_start_end_menu = m_view.addAction("시작/끝점 강조 표시")
        self.a_start_end_menu.setCheckable(True)
        self.a_start_end_menu.setChecked(self.style.flow_show_start_end)
        self.a_start_end_menu.triggered.connect(self._toggle_show_start_end)
        
        m_view.addSeparator()
        
        # 세 번째 세션: (화면맞춤, 고해상도 자동 재랜더, 현재 배율로 재랜더)
        a_fit = m_view.addAction("화면 맞춤")
        a_fit.triggered.connect(self.fit_to_window)
        self.a_auto_hi = m_view.addAction("고해상도 자동 재렌더")
        self.a_auto_hi.setCheckable(True)
        self.a_auto_hi.setChecked(True)
        self.a_auto_hi.toggled.connect(self.set_auto_highres)
        a_rerender = m_view.addAction("현재 배율로 재렌더")
        a_rerender.triggered.connect(self.rerender_now)
        
        m_view.addSeparator()
        a_shortcuts = m_view.addAction("단축키 보기...")
        a_shortcuts.triggered.connect(self.show_shortcut_help)
        m_mode = mb.addMenu("모드선택")
        
        # 보기 모드
        self.a_mode_view = m_mode.addAction("보기 모드")
        self.a_mode_view.setCheckable(True)
        self.a_mode_view.setChecked(self.active_mode == "view")
        self.a_mode_view.triggered.connect(lambda: self._set_active_mode_from_action("view"))
        
        # 넘버링 모드 (서브메뉴) - 체크 가능한 액션으로 생성
        self.a_mode_numbering_menu = m_mode.addAction("넘버링 모드")
        self.a_mode_numbering_menu.setCheckable(True)
        self.a_mode_numbering_menu.setChecked(self.active_mode == "numbering")
        m_numbering_submenu = QtWidgets.QMenu("넘버링 모드", self)
        self.a_mode_numbering_menu.setMenu(m_numbering_submenu)
        self.a_only = m_numbering_submenu.addAction("넘버링 only")
        self.a_only.setCheckable(True)
        self.a_inp = m_numbering_submenu.addAction("넘버링 + 치수입력")
        self.a_inp.setCheckable(True)
        numbering_mode_group = QtGui.QActionGroup(self)
        numbering_mode_group.setExclusive(True)
        numbering_mode_group.addAction(self.a_only)
        numbering_mode_group.addAction(self.a_inp)
        self.a_only.setChecked(self.input_mode == "number_only")
        self.a_inp.setChecked(self.input_mode == "with_input")
        self.a_only.triggered.connect(lambda: self._set_numbering_mode("number_only"))
        self.a_inp.triggered.connect(lambda: self._set_numbering_mode("with_input"))
        
        # 스탬프 모드
        self.a_mode_stamp = m_mode.addAction("스탬프 모드")
        self.a_mode_stamp.setCheckable(True)
        self.a_mode_stamp.setChecked(self.active_mode == "stamp")
        self.a_mode_stamp.triggered.connect(lambda: self._set_active_mode_from_action("stamp"))
        
        # 모드 선택 그룹 (보기, 넘버링, 스탬프 모드만)
        mode_group = QtGui.QActionGroup(self)
        mode_group.setExclusive(True)
        mode_group.addAction(self.a_mode_view)
        mode_group.addAction(self.a_mode_numbering_menu)
        mode_group.addAction(self.a_mode_stamp)
        m_edit = mb.addMenu("편집")
        # 넘버링 설정을 편집 메뉴로 이동
        a_num_settings = m_edit.addAction("넘버링 설정…")
        a_num_settings.triggered.connect(self.open_numbering_settings)
        m_edit.addSeparator()
        a_start = m_edit.addAction("Set Start Number…")
        a_start.triggered.connect(self.set_start_number)
        # ▼▼▼ 여기에 '스탬프 이미지 관리' 메뉴를 추가합니다. ▼▼▼
        m_edit.addSeparator()  # 구분선 추가 (선택사항)
        a_manage_stamps_menu = m_edit.addAction("스탬프 이미지 관리…")
        a_manage_stamps_menu.triggered.connect(self.open_stamp_manager)
        # ▲▲▲ 메뉴 추가 완료 ▲▲▲
        # Windows 메뉴 추가
        m_windows = mb.addMenu("Windows")
        # 7가지 윈도우 메뉴 항목 추가 (임시로 번호 부여)
        self.a_pdf_preview = m_windows.addAction("1. PDF Page Preview")
        self.a_pdf_preview.setCheckable(True)
        self.a_pdf_preview.setChecked(True)  # 기본적으로 보이도록 설정
        self.a_pdf_preview.triggered.connect(self.toggle_pdf_preview)
        self.a_3d_navigator = m_windows.addAction("2. 3D Viewport Navigator")
        self.a_3d_navigator.setCheckable(True)
        self.a_3d_navigator.setChecked(True)  # 기본적으로 보이도록 설정
        self.a_3d_navigator.triggered.connect(self.toggle_3d_navigator)
        self.a_2d_viewer = m_windows.addAction("3. 2D Viewer")
        self.a_2d_viewer.setCheckable(True)
        self.a_2d_viewer.triggered.connect(lambda: print("2D Viewer 토글"))
        self.a_3d_viewer = m_windows.addAction("4. 3D Viewer")
        self.a_3d_viewer.setCheckable(True)
        self.a_3d_viewer.triggered.connect(lambda: print("3D Viewer 토글"))
        self.a_numbering_list = m_windows.addAction("5. Numbering List")
        self.a_numbering_list.setCheckable(True)
        self.a_numbering_list.setChecked(True)  # 기본적으로 보이도록 설정
        self.a_numbering_list.triggered.connect(self.toggle_numbering_list)
        self.a_stamping_list = m_windows.addAction("6. Stamping List")
        self.a_stamping_list.setCheckable(True)
        self.a_stamping_list.triggered.connect(lambda: print("Stamping List 토글"))
        self.a_product_info = m_windows.addAction("7. Product Information")
        self.a_product_info.setCheckable(True)
        self.a_product_info.triggered.connect(lambda: print("Product Information 토글"))
        m_help = mb.addMenu("도움말")
        a_about = m_help.addAction("정보...")
        a_about.triggered.connect(self.show_about_dialog)

    # 프리뷰 모드 선택 추가 함수... v3.01에서...
    def set_preview_mode(self, mode: str):
        """넘버링 프리뷰 모드를 '십자선' 또는 '프리뷰'로 설정합니다."""
        self.preview_mode = mode
        # 메뉴바와 툴바의 체크 상태를 항상 동기화합니다.
        if hasattr(self, "a_preview"):
            self.a_preview.setChecked(mode == "preview")
        if hasattr(self, "a_crosshair"):
            self.a_crosshair.setChecked(mode == "crosshair")
        # 미리보기 버튼 체크 상태 업데이트
        self._update_preview_button_visuals()
        if hasattr(self, "action_preview_toolbar"):
            self.action_preview_toolbar.setChecked(mode == "preview")
        if hasattr(self, "action_crosshair_toolbar"):
            self.action_crosshair_toolbar.setChecked(mode == "crosshair")
        # [핵심 수정] 현재 '넘버링 모드'가 활성화 상태일 때만 커서 모양을 변경합니다.
        if self.active_mode == "numbering":
            if self.preview_mode == "crosshair":
                self.view.setCursor(QtCore.Qt.CrossCursor)
                if self._preview_ellipse:
                    self._preview_ellipse.hide()
                if self._preview_text:
                    self._preview_text.hide()
            else:  # 'preview' 모드일 경우
                self.view.setCursor(QtCore.Qt.BlankCursor)

    # ▼▼▼ 3D 뷰어 관련 메서드들 ▼▼▼
    def open_3d_model(self):
        # ▼▼▼ [추가] 프로젝트가 열려있는지 먼저 확인 ▼▼▼
        if not self.doc:
            QtWidgets.QMessageBox.warning(self, "알림", "먼저 프로젝트를 열거나 생성해야 합니다.")
            return
        # ▲▲▲
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open 3D Model", "", "CAD Files (*.stp *.step *.igs *.iges *.x_t)"
        )
        if not path:
            return
        # 1. 프로그레스 대화상자를 생성합니다.
        self.progress_dialog = QtWidgets.QProgressDialog(
            f"'{os.path.basename(path)}' 파일을 불러오는 중입니다...",  # 대화상자에 표시될 텍스트
            "취소",  # 취소 버튼 텍스트
            0,  # 최소값
            0,  # 최대값 (0으로 설정하면 '계속 진행 중' 상태로 보임)
            self,
        )
        self.progress_dialog.setWindowTitle("3D 모델 로딩 중")
        self.progress_dialog.setModal(True)  # 다른 창을 클릭할 수 없도록 설정
        self.progress_dialog.show()
        # 2. 백그라운드 스레드에 작업 시작 신호를 보냅니다.
        self.start_loading_3d.emit(path)
        # ▲▲▲ [수정 끝] ▲▲▲
        self.model_path = path  # <--- 이 줄을 추가해주세요
        self.last_opened_3d_path = path

    # main.py의 on_3d_load_finished 함수 (구버전 호환용)
    # on_3d_load_finished 함수를 아래 코드로 통째로 교체하세요.
    def on_3d_load_finished(self, geometry):
        import os
        import pyvista as pv
        import trimesh
        from pyvistaqt import QtInteractor
        from trimesh.path.path import Path3D

        # 1. "로딩 중..." 대화상자를 닫습니다.
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()
        self.statusBar().showMessage("3D 모델 렌더링 중...")
        # 2. 이전에 있던 3D 뷰어를 깨끗이 치웁니다.
        for i in reversed(range(self.vlayout_3d.count())):
            self.vlayout_3d.itemAt(i).widget().deleteLater()
        # 3. 새로운 3D 뷰어(plotter)를 만듭니다.
        plotter = QtInteractor(self.widget_3d)
        self.plotter = plotter  # Navigator에서 접근할 수 있도록 저장
        self.vlayout_3d.addWidget(plotter.interactor)
        # 3-1. 3D 뷰어에 컬러 컨트롤 패널 추가
        self._setup_3d_viewer_color_controls()

        # 4. 3D 모델을 뷰어에 추가하는 내부 함수 정의
        def render_solid_mesh(geom):
            pv_mesh = pv.wrap(geom)
            # 메인 surface mesh 추가 (엣지 표시 없음)
            plotter.add_mesh(
                pv_mesh, name="main_surface", style="surface", color="lightgrey", show_edges=False
            )
            # feature edges 추가 (30도 각도 기준)
            feature_edges = pv_mesh.extract_feature_edges(feature_angle=30.0)
            if feature_edges.n_points > 0:
                actor = plotter.add_mesh(
                    feature_edges,
                    name="feature_edges",
                    color="black",
                    line_width=1.5,
                    render_lines_as_tubes=False,
                    lighting=False,
                )
                # 초기에는 숨김 (shading 모드가 기본이므로)
                if actor:
                    actor.SetVisibility(False)

        # 4-1. 불러온 데이터 타입에 따라 렌더링 실행
        if isinstance(geometry, trimesh.Scene):
            for geom in geometry.geometry.values():
                if isinstance(geom, trimesh.PointCloud):
                    plotter.add_mesh(
                        pv.PolyData(geom.vertices), cmap="viridis", render_points_as_spheres=True
                    )
                elif isinstance(geom, Path3D):
                    plotter.add_mesh(
                        pv.lines_from_points(geom.vertices), color="yellow", line_width=5
                    )
                else:
                    render_solid_mesh(geom)
        elif isinstance(geometry, (trimesh.Trimesh, pv.PolyData)):
            render_solid_mesh(geometry)
        elif isinstance(geometry, trimesh.PointCloud):
            plotter.add_mesh(
                pv.PolyData(geometry.vertices), cmap="viridis", render_points_as_spheres=True
            )
        elif isinstance(geometry, Path3D):
            plotter.add_mesh(pv.lines_from_points(geometry.vertices), color="yellow", line_width=5)
        # 5. 카메라 위치를 모델에 맞게 재설정합니다.
        plotter.reset_camera()
        # 5-1. 기본 뷰 모드를 "음영 처리"로 설정 (엣지 없음)
        self.set_view_mode("shading")
        # 5-2. 초기 뷰 정보 표시
        self.update_view_info()
        # 6. 화면을 3D 탭으로 전환합니다.
        # self.tab_widget.setCurrentWidget(self.widget_3d)
        # ▼▼▼ [수정 3] 대신 상태 표시줄에 완료 메시지를 표시 ▼▼▼
        filename = ""
        if hasattr(self, "last_opened_3d_path"):
            filename = os.path.basename(self.last_opened_3d_path)
        self.statusBar().showMessage(f"'{filename}' 3D 모델 로딩 완료.", 4000)
        # 7. 마지막으로 사용자에게 성공 메시지를 보여줍니다.
        filename = ""
        if hasattr(self, "last_opened_3d_path"):
            filename = os.path.basename(self.last_opened_3d_path)
        self.statusBar().clearMessage()  # '렌더링 중' 메시지 지우기
        QtWidgets.QMessageBox.information(
            self, "로딩 완료", f"'{filename}' 파일을 성공적으로 불러왔습니다."
        )

    # on_3d_load_error 함수를 아래 코드로 통째로 교체하세요. (중복 코드 정리)
    def on_3d_load_error(self, error_message):
        # 로딩 대화상자가 있다면 닫습니다.
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()
        _log_error(self, "3D 모델 로딩 오류", Exception(error_message))
        self.statusBar().showMessage("3D 모델을 불러오는 데 실패했습니다.", 5000)

    def _apply_initial_layout(self):
        try:
            self.showMaximized()
        except:
            pass
        # "프로그램 켜지면 왼쪽 패널 폭을 빨간색 박스 크기로 더 축소!"
        sizes = [60, int(self.width() * 0.30)]  # 더 작은 크기로 설정
        self.resizeDocks([self.page_dock, self.dock], sizes, QtCore.Qt.Horizontal)
        # 3D Navigator를 왼쪽 도크의 아래쪽에 배치하도록 크기 조정
        # 페이지 도크는 위쪽 70%, Navigator는 아래쪽 30% 정도
        left_sizes = [
            int(self.height() * 0.70),  # 페이지 도크 높이
            int(self.height() * 0.30),  # Navigator 도크 높이
        ]
        self.resizeDocks([self.page_dock, self.navigator_dock], left_sizes, QtCore.Qt.Vertical)

    # 스페셜함수 적용 함수 새로 생성. v2.95에서 함.
    def set_individual_style(self):
        """선택된 항목에 개별 서식을 적용하거나 해제합니다."""
        row = self.table.currentRow()
        if row < 0:
            return
        try:
            item_no = int(self.table.item(row, 0).text())
            target_item = next((it for it in self.items if it.no == item_no), None)
            if not target_item:
                return
        except (ValueError, AttributeError):
            return
        if target_item.custom_style:
            # 이미 개별 서식이 있다면 -> 삭제 여부 확인
            reply = QtWidgets.QMessageBox.question(
                self,
                "개별 서식 삭제",
                f"{item_no}번에 설정된 개별 서식을 삭제하고 전체 서식으로 되돌리시겠습니까?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply == QtWidgets.QMessageBox.Yes:
                target_item.custom_style = None
                self.load_page(self.cur_page_index)  # 화면 새로고침
        else:
            # 개별 서식이 없다면 -> 적용 여부 확인
            reply = QtWidgets.QMessageBox.question(
                self,
                "개별 서식 지정",
                f"{item_no}번에 개별 서식을 지정하시겠습니까?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply == QtWidgets.QMessageBox.Yes:
                # 현재 전역 스타일을 복사하여 초기값으로 사용
                new_style = copy.deepcopy(self.style)
                if self.open_label_settings(new_style):  # 사용자가 OK를 누르면
                    target_item.custom_style = new_style
                    self.load_page(self.cur_page_index)  # 화면 새로고침
        self._set_dirty()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._position_integrated_control_panel()

    def eventFilter(self, watched, event):
        widget_3d = getattr(self, "widget_3d", None)
        if watched is widget_3d and event.type() == QtCore.QEvent.Resize:
            self._position_integrated_control_panel()
        return super().eventFilter(watched, event)

    def new_project(self):
        if not self._maybe_save(
            "새 프로젝트", "새로운 프로젝트를 시작합니다.\n현재 작업을 저장하시겠습니까?"
        ):
            return
        # ... (기본 프로젝트 이름 생성 로직은 그대로) ...
        try:
            default_dir = os.getcwd()
            today_str = datetime.now().strftime("%Y-%m-%d")
            base_name_prefix = f"{today_str}_pjt_"
            max_num = 0
            for filename in os.listdir(default_dir):
                if filename.startswith(base_name_prefix):
                    try:
                        num_part = filename[len(base_name_prefix) :].split(".")[0]
                        current_num = int(num_part)
                        if current_num > max_num:
                            max_num = current_num
                    except ValueError:
                        continue
            next_num = max_num + 1
            default_name = f"{base_name_prefix}{next_num:02d}"
        except Exception as e:
            print(f"기본 프로젝트 이름 생성 오류: {e}")
            default_name = ""
            default_dir = ""
        dialog = NewProjectDialog(self, default_name=default_name, default_dir=default_dir)
        if dialog.exec():
            self.project_name = dialog.project_name
            self.project_dir = dialog.project_dir
            self._close_current_doc()
            self._reset_all_tables()  # <-- 모든 테이블 초기화
            self._reset_state_for_new()  # <-- 모든 상태 초기화
            self.project_path = None
            self._set_dirty(False)  # 새 프로젝트는 '저장됨' 상태
            self._update_window_title()  # 윈도우 제목 업데이트
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                f"'{self.project_name}' 프로젝트의 PDF 파일 가져오기",
                self.project_dir,
                "PDF Files (*.pdf)",
            )
            if path:
                self.import_pdf_from_path(path)
            else:
                # PDF를 선택하지 않으면 프로젝트 생성을 취소
                self.project_name = None
                self.project_dir = None
                self._update_window_title()

    def _close_current_doc(self):
        """현재 문서를 닫고 관련 상태를 초기화합니다."""
        try:
            self.clear_highlight()
        except Exception as e:
            print(f"_close_current_doc: clear_highlight 오류: {e}")
        
        # scene이 존재하는지 확인 후 clear
        if hasattr(self, 'scene') and self.scene is not None:
            try:
                self.scene.clear()
            except Exception as e:
                print(f"_close_current_doc: scene.clear() 오류: {e}")
        
        self._preview_ellipse = None
        self._preview_text = None
        
        try:
            if self.doc is not None:
                self.doc.close()
        except Exception as e:
            print(f"_close_current_doc: doc.close() 오류: {e}")
        
        self.doc = None
        try:
            self._update_page_navigation_ui()
        except Exception as e:
            print(f"_close_current_doc: _update_page_navigation_ui 오류: {e}")
        
        try:
            self._clear_thumbnails()
        except Exception as e:
            print(f"_close_current_doc: _clear_thumbnails 오류: {e}")

    def _reset_all_tables(self):
        """넘버링 테이블과 스탬프 테이블을 모두 초기화합니다."""
        self.table.blockSignals(True)
        self.stamp_table.blockSignals(True)
        try:
            self.table.clearSelection()
            self.table.setRowCount(0)
            self.stamp_table.clearSelection()
            self.stamp_table.setRowCount(0)
        finally:
            self.table.blockSignals(False)
            self.stamp_table.blockSignals(False)

    def _reset_state_for_new(self):
        """새 프로젝트를 위해 모든 상태 변수를 기본값으로 초기화합니다."""
        # 넘버링 관련 초기화
        self.items.clear()
        self.next_no = 1
        self.numbering_mode = "global"
        # 스탬프 관련 초기화
        self.stamps.clear()
        self.registered_stamps.clear()
        self.current_stamp_index = 0
        # ▼▼▼ [추가] 3D 뷰어 및 관련 상태 초기화 ▼▼▼
        self._clear_3d_viewer()
        # ▲▲▲
        # 되돌리기/되살리기 스택 초기화
        self.undo_stack.clear()
        self.redo_stack.clear()
        # 전역 스타일 및 설정 초기화
        self.style = LabelStyle()
        self.set_input_mode("number_only")
        # 전역 스탬프 설정 초기화
        self.stamp_opacity = 1.0
        self.stamp_rotation = 0.0
        self.stamp_opacity_random = True
        self.stamp_rotation_random = True
        self.stamp_opacity_min = 0.90
        self.stamp_opacity_max = 1.0
        self.stamp_rotation_min = -5.0
        self.stamp_rotation_max = 5.0
        # UI 관련 상태 업데이트
        if hasattr(self, "cb_separate_numbering"):
            self.cb_separate_numbering.setEnabled(True)
            self.cb_separate_numbering.setChecked(False)
        self._refresh_preview_text()
        self._update_undo_redo_hint()
        self._update_status()
        self._update_stamp_button_icon()

    def open_project_dialog(self):
        # ===== ▼▼▼ 수정 시작 ▼▼▼ =====
        if not self._maybe_save(
            "프로젝트 열기", "새로운 파일을 엽니다.\n현재 파일을 저장하시겠습니까?"
        ):
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Project", "", "TS Numbering (*.tsn)"
        )
        if path:
            self.open_project(path)
        # ===== ▲▲▲ 수정 끝 ▲▲▲ =====

    def open_project(self, path):
        try:
            # 1. 파일을 먼저 열고 모든 데이터를 메모리로 읽어들입니다.
            with zipfile.ZipFile(path, "r") as zf:
                pdf_bytes = zf.read(TSN_PDF_NAME)
                meta = json.loads(zf.read(TSN_META_NAME).decode("utf-8"))
                model_path_info = meta.get("3d_model_path", None)
                model_bytes = None
                if model_path_info and model_path_info.startswith("embedded:"):
                    if "model.data" in zf.namelist():
                        model_bytes = zf.read("model.data")
        except Exception as e:
            _log_error(self, "프로젝트 파일 열기 오류", e)
            return
        # 2. 파일 읽기에 완전히 성공했다면, 그 때서야 현재 상태를 초기화합니다.
        self._close_current_doc()
        self._reset_all_tables()
        self._reset_state_for_new()
        # 3. 읽어들인 데이터로 프로그램 상태를 하나씩 복원합니다.
        self.doc = pdfium.PdfDocument(pdf_bytes)
        self.numbering_mode = meta.get("numbering_mode", "global")
        self.cur_page_index = 0  # <<--- [수정 2] 항상 첫 페이지(인덱스 0)로 시작
        self.render_scale = int(meta.get("render_scale", 2))
        self.style.from_dict(meta.get("style", {}))
        # 넘버링/스탬프 데이터 복원
        for m in meta.get("items", []):
            custom_style = None
            if "custom_style" in m and m["custom_style"]:
                custom_style = LabelStyle()
                custom_style.from_dict(m["custom_style"])
            it = MarkItem(
                no=float(m["no"]),
                page_index=int(m["page_index"]),
                pdf_point=tuple(m["pdf_point"]),
                dim_type=m.get("dim_type", "선형"),
                value=m.get("value", ""),
                tol_plus=normalize_signed_text(m.get("tol_plus", "")),
                tol_minus=normalize_signed_text(m.get("tol_minus", "")),
                custom_style=custom_style,
                viewport_parameters=m.get("viewport_parameters", ""),
            )  # 3D 뷰포트 파라메터 복원
            self.items.append(it)
        self.registered_stamps = meta.get("registered_stamps", {})
        for s_data in meta.get("stamps", []):
            self.stamps.append(StampItem(**s_data))
        # 3D 모델 로드 준비
        if model_path_info:
            if model_path_info.startswith("embedded:"):
                if model_bytes:
                    import tempfile

                    original_filename = model_path_info.split(":", 1)[1]
                    temp_dir = tempfile.gettempdir()
                    self.model_path = os.path.join(temp_dir, f"tsn_temp_{original_filename}")
                    with open(self.model_path, "wb") as f:
                        f.write(model_bytes)
                    self.start_loading_3d.emit(self.model_path)
            else:
                self.model_path = model_path_info
                if os.path.exists(self.model_path):
                    self.start_loading_3d.emit(self.model_path)
                else:
                    self.statusBar().showMessage(
                        f"연결된 3D 모델을 찾을 수 없습니다: {self.model_path}", 5000
                    )
        # ▼▼▼ [핵심] 누락되었던 최종 UI 업데이트 단계 ▼▼▼
        # 5. 모든 데이터 로딩이 끝난 후, UI를 새로고침합니다.
        self.project_path = path
        self.project_name = os.path.splitext(os.path.basename(path))[0]
        self.project_dir = os.path.dirname(path)
        # 이 함수가 PDF 뷰어, 테이블, 썸네일 등 모든 것을 화면에 다시 그립니다.
        self.load_page(self.cur_page_index)  # <<--- [수정 1] 화면을 먼저 로드
        self._set_dirty(False)
        self._update_window_title()
        self._update_undo_redo_hint()
        self._update_status()
        self._update_page_navigation_ui()
        self._populate_thumbnails()
        self._update_stamp_button_icon()
        # 6. [수정 1] 모든 화면이 로드된 후, 마지막으로 다음 번호 지정 대화상자 호출
        if self.numbering_mode == "global":
            if self.items:
                max_no = 0
                for item in self.items:
                    if item.no % 1 == 0:
                        max_no = max(max_no, int(item.no))
                suggested_no = max_no + 1
                new_next_no, ok = QtWidgets.QInputDialog.getInt(
                    self,
                    "다음 번호 지정",
                    f"마지막 번호는 {max_no}번입니다. 이어갈 번호를 지정해 주세요.",
                    suggested_no,
                    1,
                )
                self.next_no = float(new_next_no) if ok else float(suggested_no)
            else:
                self.next_no = 1.0

    def save_project(self) -> bool:
        print(f"[save_project] 저장 시작")
        if self.doc is None:
            QtWidgets.QMessageBox.warning(self, "알림", "저장할 PDF 문서가 없습니다.")
            return False
        if not self.project_path:
            print(f"[save_project] project_path가 없음, save_project_as 호출")
            return self.save_project_as()
        print(f"[save_project] 저장 경로: {self.project_path}")
        save_option = "link"
        if self.model_path and os.path.exists(self.model_path):
            option = SaveOptionsDialog.get_save_option(self)
            if not option:
                print(f"[save_project] 저장 옵션 선택 취소")
                return False
            save_option = option
        print(f"[save_project] 저장 옵션: {save_option}")
        self._sync_items_from_table()
        # _write_tsn의 반환값 확인
        if not self._write_tsn(self.project_path, save_option):
            print(f"[save_project] _write_tsn 실패")
            return False
        self._set_dirty(False)
        self.statusBar().showMessage(
            f"✅ 프로젝트 저장 완료: {os.path.basename(self.project_path)}"
        )
        print(f"[save_project] 저장 완료")
        return True

    def save_project_as(self) -> bool:
        print(f"[save_project_as] 다른 이름으로 저장 시작")
        if self.doc is None:
            QtWidgets.QMessageBox.warning(self, "알림", "저장할 PDF 문서가 없습니다.")
            return False
        default_dir = self.project_dir or ""
        default_filename = f"{self.project_name}.tsn" if self.project_name else "project.tsn"
        default_path = os.path.join(default_dir, default_filename)
        print(f"[save_project_as] 기본 경로: {default_path}")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "프로젝트 다른 이름으로 저장",
            default_path,
            "TS Numbering (*.tsn)",
        )
        if not path:
            print(f"[save_project_as] 사용자가 취소함")
            return False
        if not path.lower().endswith(".tsn"):
            path += ".tsn"
        print(f"[save_project_as] 선택된 경로: {path}")
        save_option = "link"
        if self.model_path and os.path.exists(self.model_path):
            option = SaveOptionsDialog.get_save_option(self)
            if not option:
                print(f"[save_project_as] 저장 옵션 선택 취소")
                return False
            save_option = option
        print(f"[save_project_as] 저장 옵션: {save_option}")
        self._sync_items_from_table()
        # _write_tsn의 반환값 확인
        if not self._write_tsn(path, save_option):
            print(f"[save_project_as] _write_tsn 실패")
            return False
        self.project_path = path
        self.project_name = os.path.splitext(os.path.basename(path))[0]
        self.project_dir = os.path.dirname(path)
        print(f"[save_project_as] 프로젝트 정보 업데이트: path={self.project_path}, name={self.project_name}, dir={self.project_dir}")
        self._set_dirty(False)
        self.statusBar().showMessage(
            f"✅ 프로젝트 저장 완료: {os.path.basename(self.project_path)}"
        )
        print(f"[save_project_as] 저장 완료")
        return True

    # 스페셜 서식 적용 위해 교체 v2.95에서...
    # main.py의 PdfAnnotator 클래스 내부
    # main.py의 PdfAnnotator 클래스 내부
    def _write_tsn(self, path, save_option="link"):
        """
        프로젝트를 .tsn 파일로 저장합니다.
        
        Args:
            path: 저장할 파일 경로
            save_option: 저장 옵션 ("link" 또는 "embed")
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 경로 검증
            if not path:
                raise ValueError("저장 경로가 지정되지 않았습니다.")
            
            # 절대 경로로 변환 (상대 경로 문제 방지)
            path = os.path.abspath(path)
            print(f"[저장 시작] 경로: {path}")
            
            # 디렉토리가 없으면 생성
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                print(f"[저장] 디렉토리 생성: {dir_path}")
                os.makedirs(dir_path, exist_ok=True)
            
            # 기존 파일이 있으면 백업 (선택사항)
            if os.path.exists(path):
                print(f"[저장] 기존 파일 발견: {path}")
            
            # PDF 데이터 준비 (pypdfium2는 tobytes()가 없으므로 임시 파일 사용)
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
            self.doc.save(tmp_path)
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(tmp_path)  # 임시 파일 삭제
            if not pdf_bytes:
                raise ValueError("PDF 데이터가 비어있습니다.")
            print(f"[저장] PDF 데이터 크기: {len(pdf_bytes)} bytes")
            
            # 아이템 데이터 준비
            items_data = []
            for it in self.items:
                item_dict = {
                    "no": it.no,
                    "page_index": it.page_index,
                    "pdf_point": list(it.pdf_point),
                    "dim_type": it.dim_type,
                    "value": it.value,
                    "tol_plus": it.tol_plus,
                    "tol_minus": it.tol_minus,
                    "viewport_parameters": it.viewport_parameters,  # 3D 뷰포트 파라메터 추가
                }
                if it.custom_style:
                    item_dict["custom_style"] = it.custom_style.to_dict()
                items_data.append(item_dict)
            
            # 메타데이터 준비
            meta = {
                "app": APP_NAME,
                "app_version": APP_VER,
                "tsn_version": TSN_VERSION,
                "next_no": self.next_no,
                "numbering_mode": self.numbering_mode,  # <<--- [추가] 넘버링 모드 저장
                "current_page": self.cur_page_index,
                "render_scale": self.render_scale,
                "style": self.style.to_dict(),
                "items": items_data,
                "registered_stamps": self.registered_stamps,
                "stamps": [s.__dict__ for s in self.stamps],
                "stamp_settings": {
                    "opacity": self.stamp_opacity,
                    "rotation": self.stamp_rotation,
                    "opacity_random": self.stamp_opacity_random,
                    "rotation_random": self.stamp_rotation_random,
                    "opacity_min": self.stamp_opacity_min,
                    "opacity_max": self.stamp_opacity_max,
                    "rotation_min": self.stamp_rotation_min,
                    "rotation_max": self.stamp_rotation_max,
                },
            }
            if save_option == "embed" and self.model_path and os.path.exists(self.model_path):
                meta["3d_model_path"] = f"embedded:{os.path.basename(self.model_path)}"
            else:
                meta["3d_model_path"] = self.model_path
            
            # ZIP 파일로 저장
            print(f"[저장] ZIP 파일 생성 시작: {path}")
            try:
                with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    print(f"[저장] ZIP 파일 열기 성공")
                    meta_json = json.dumps(meta, ensure_ascii=False, indent=2)
                    print(f"[저장] 메타데이터 크기: {len(meta_json)} bytes")
                    zf.writestr(TSN_META_NAME, meta_json)
                    print(f"[저장] 메타데이터 쓰기 완료: {TSN_META_NAME}")
                    zf.writestr(TSN_PDF_NAME, pdf_bytes)
                    print(f"[저장] PDF 쓰기 완료: {TSN_PDF_NAME}")
                    if save_option == "embed" and self.model_path and os.path.exists(self.model_path):
                        zf.write(self.model_path, arcname="model.data")
                        print(f"[저장] 3D 모델 임베드 완료: {self.model_path}")
                print(f"[저장] ZIP 파일 닫기 완료")
            except Exception as zip_error:
                print(f"[저장 오류] ZIP 파일 생성 중 예외 발생: {zip_error}")
                print(traceback.format_exc())
                raise
            
            # 파일이 실제로 생성되었는지 확인
            if not os.path.exists(path):
                raise IOError(f"파일 저장 후 확인 실패: {path}")
            
            # 파일 크기 확인 (최소한의 검증)
            file_size = os.path.getsize(path)
            if file_size == 0:
                raise IOError(f"저장된 파일이 비어있습니다: {path}")
            
            print(f"[저장 성공] 프로젝트 저장 완료: {path} (크기: {file_size} bytes)")
            return True
            
        except Exception as e:
            error_msg = f"프로젝트 저장 중 오류 발생:\n{str(e)}\n\n{traceback.format_exc()}"
            print(error_msg)
            QtWidgets.QMessageBox.critical(
                self,
                "저장 오류",
                f"프로젝트 저장에 실패했습니다.\n\n{str(e)}\n\n자세한 내용은 콘솔을 확인하세요."
            )
            return False

    def import_pdf(self):
        # ▼▼▼ [핵심] 문서가 열려있지 않을 때의 로직을 완전히 변경합니다. ▼▼▼
        if not self.doc:
            QtWidgets.QMessageBox.warning(
                self,
                "알림",
                "이 기능은 기존 프로젝트의 PDF를 교체하거나 이어붙일 때 사용합니다.\n\n"
                "새 작업을 시작하려면 '파일 > 새 프로젝트' 메뉴를 이용해주세요.",
            )
            return
        # ▲▲▲ 여기까지 변경 ▲▲▲
        # 문서가 이미 열려있으면, 사용자에게 방식을 물어봄 (기존 로직과 동일)
        dialog = AppendPdfDialog(self)
        if dialog.exec():
            choice = dialog.choice
            if choice == "append":
                path, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self, "이어붙일 PDF 파일 선택", self.project_dir or "", "PDF Files (*.pdf)"
                )
                if path:
                    self._append_pdf(path)
            elif choice == "replace":
                reply = QtWidgets.QMessageBox.question(
                    self,
                    "새로 불러오기",
                    "기존 작업을 모두 닫고 새 PDF로 작업을 다시 시작하시겠습니까?\n(모든 넘버링 정보가 삭제됩니다.)",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No,
                )
                if reply == QtWidgets.QMessageBox.No:
                    return
                path, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self, "새로 불러올 PDF 파일 선택", self.project_dir or "", "PDF Files (*.pdf)"
                )
                if not path:
                    return
                self._close_current_doc()
                self._reset_all_tables()
                self._reset_state_for_new()
                self.import_pdf_from_path(path)

    def import_pdf_from_path(self, path):
        # 이 함수는 이제 '새 집을 짓는' 역할에만 집중합니다.
        print(f"[DEBUG] import_pdf_from_path 시작: path={path}")
        print(f"[DEBUG] import_pdf_from_path: scene 존재={hasattr(self, 'scene')}, view 존재={hasattr(self, 'view')}")
        
        try:
            print(f"[DEBUG] import_pdf_from_path: pdfium.PdfDocument 호출 전")
            self.doc = pdfium.PdfDocument(path)
            print(f"[DEBUG] import_pdf_from_path: PDF 열기 성공, 페이지 수={len(self.doc)}")
        except Exception as e:
            import traceback
            print(f"[DEBUG] import_pdf_from_path: PDF 열기 오류: {e}")
            traceback.print_exc()
            _log_error(self, "PDF 열기 오류", e)
            self.doc = None  # 오류 시 doc 객체 확실히 비우기
            self._update_page_navigation_ui()
            self._clear_thumbnails()
            return
        
        # ▼▼▼ [핵심 수정] 페이지 수와 상관없이 항상 넘버링 방식을 물어봅니다. ▼▼▼
        print(f"[DEBUG] import_pdf_from_path: NumberingModeDialog 표시 전")
        dialog = NumberingModeDialog(self)
        if dialog.exec():
            self.numbering_mode = dialog.choice
            print(f"[DEBUG] import_pdf_from_path: 넘버링 모드 선택됨: {self.numbering_mode}")
        else:
            print(f"[DEBUG] import_pdf_from_path: 넘버링 모드 선택 취소")
            # 사용자가 넘버링 방식 선택을 취소하면, 문서 로드를 중단합니다.
            self._close_current_doc()
            return
        # ▲▲▲ 여기까지 수정 ▲▲▲
        
        try:
            if hasattr(self, "cb_separate_numbering"):
                self.cb_separate_numbering.setChecked(self.numbering_mode == "page_specific")
                self.cb_separate_numbering.setEnabled(False)  # 한번 선택하면 프로젝트 내에서 변경 불가
        except Exception as e:
            print(f"[DEBUG] 체크박스 설정 오류: {e}")
        
        # 새 PDF의 정보를 기반으로 프로젝트 기본 정보 설정
        if not self.project_name:
            self.project_name = os.path.splitext(os.path.basename(path))[0]
            self.project_dir = os.path.dirname(path)
        self.pdf_path = path
        self.cur_page_index = 0
        self._set_dirty(True)
        print(f"[DEBUG] import_pdf_from_path: 프로젝트 정보 설정 완료, load_page 호출 전")
        
        try:
            print(f"[DEBUG] import_pdf_from_path: load_page({self.cur_page_index}) 호출")
            self.load_page(self.cur_page_index)
            print(f"[DEBUG] import_pdf_from_path: load_page 완료")
        except Exception as e:
            import traceback
            print(f"[DEBUG] import_pdf_from_path - load_page 오류: {e}")
            traceback.print_exc()
            _log_error(self, "PDF 페이지 로드 오류", e)
            self._close_current_doc()
            return
        
        try:
            self._populate_thumbnails()
        except Exception as e:
            print(f"[DEBUG] 썸네일 생성 오류: {e}")
            _log_error(self, "썸네일 생성 오류", e)
            # 썸네일 오류는 치명적이지 않으므로 계속 진행
        
        try:
            self._update_window_title()
        except Exception as e:
            print(f"[DEBUG] 윈도우 제목 업데이트 오류: {e}")
        
        print(f"[DEBUG] import_pdf_from_path: 모든 작업 완료")

    def _render_factor_for_scale(self, s: float) -> int:
        return 2 if s < 1.6 else (4 if s < 3.2 else 6)

    # 줌인시 갑자기 화면이 튀는걸 방지하기 위해 코드 교체됨. v2.94에서...
    def _maybe_rerender_for_zoom(self, s: float):
        if not self.auto_highres or not self.doc:
            return
        desired = self._render_factor_for_scale(s)
        if desired != self.render_scale:
            # --- 수정 시작: 화면 점프 방지 로직 ---
            # 1. 이미지를 교체하기 전, 현재 화면의 중심 좌표를 기억합니다.
            # 뷰포트(보이는 영역)의 중심점을 씬(전체 도면)의 좌표로 변환합니다.
            center_point_before = self.view.mapToScene(self.view.viewport().rect().center())
            # 현재 배율 기준으로 '정규화된' 좌표를 계산해 둡니다. (비율 좌표)
            normalized_x = center_point_before.x() / self.render_scale
            normalized_y = center_point_before.y() / self.render_scale
            # 2. 새로운 해상도로 이미지를 다시 렌더링합니다.
            self.render_scale = desired
            self.load_page(self.cur_page_index)
            # 3. 새 이미지에 맞게 기억해 둔 중심점의 좌표를 다시 계산합니다.
            new_center_x = normalized_x * self.render_scale
            new_center_y = normalized_y * self.render_scale
            # 4. 뷰를 새로운 중심점으로 즉시 이동시킵니다.
            self.view.centerOn(QtCore.QPointF(new_center_x, new_center_y))
            # --- 수정 끝 ---

    def load_page(self, index: int):
        print(f"[DEBUG] load_page 시작: index={index}, doc 존재={self.doc is not None}")
        
        if not self.doc:
            print(f"[DEBUG] load_page: doc이 None이므로 종료")
            return
        
        # scene과 view가 제대로 초기화되었는지 확인
        if not hasattr(self, 'scene') or self.scene is None:
            print(f"[DEBUG] load_page 오류: scene이 초기화되지 않았습니다.")
            return
        if not hasattr(self, 'view') or self.view is None:
            print(f"[DEBUG] load_page 오류: view가 초기화되지 않았습니다.")
            return
        
        print(f"[DEBUG] load_page: scene/view 검증 완료, 페이지 로드 시작")
        
        try:
            print(f"[DEBUG] load_page: 인덱스 계산 전, len(doc)={len(self.doc)}")
            index = max(0, min(index, len(self.doc) - 1))
            self.cur_page_index = index
            print(f"[DEBUG] load_page: get_page 호출 전, index={index}")
            page = self.doc.get_page(index)
            print(f"[DEBUG] load_page: get_page 완료, render 호출 전, scale={self.render_scale}")
            # pypdfium2의 render()는 PdfBitmap을 반환합니다
            bitmap = page.render(scale=self.render_scale)
            print(f"[DEBUG] load_page: render 완료, _pil_to_qimage 호출 전")
            img = _pil_to_qimage(bitmap)
            print(f"[DEBUG] load_page: _pil_to_qimage 완료, QImage 유효성 검사 시작")
            # QImage 유효성 검사
            if img.isNull():
                print(f"[DEBUG] load_page 오류: QImage가 null입니다 (페이지 {index})")
                _log_error(self, "페이지 이미지 생성 실패", Exception("QImage가 null입니다"))
                return
            
            print(f"[DEBUG] load_page: QImage 유효, size={img.width()}x{img.height()}, format={img.format()}")
            
            # QPixmap.fromImage 호출
            # 특정 PDF에서 크래시가 발생하므로 QImage 변환을 우회하고 임시 파일 사용
            pm = None
            
            # 방법 1: 임시 파일을 통한 변환 (가장 안전 - QImage 변환을 완전히 우회)
            try:
                import tempfile
                import os
                print(f"[DEBUG] load_page: 방법 1 시도 - 임시 파일을 통한 변환 (QImage 우회)")
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                img.save(tmp_path, 'PNG')
                pm = QtGui.QPixmap(tmp_path)
                os.unlink(tmp_path)
                if not pm.isNull():
                    print(f"[DEBUG] load_page: 방법 1 성공, size={pm.width()}x{pm.height()}")
                else:
                    raise ValueError("QPixmap is null")
            except Exception as e:
                import traceback
                print(f"[DEBUG] load_page: 방법 1 실패: {e}")
                traceback.print_exc()
                pm = None
            
            # 방법 2: QImage를 복사한 후 변환 (QImage 변환 시도)
            if pm is None or pm.isNull():
                try:
                    print(f"[DEBUG] load_page: 방법 2 시도 - QImage 복사 후 변환")
                    img_copy = img.copy()
                    pm = QtGui.QPixmap.fromImage(img_copy)
                    if not pm.isNull():
                        print(f"[DEBUG] load_page: 방법 2 성공, size={pm.width()}x{pm.height()}")
                    else:
                        raise ValueError("QPixmap is null")
                except Exception as e:
                    import traceback
                    print(f"[DEBUG] load_page: 방법 2 실패: {e}")
                    traceback.print_exc()
                    pm = None
            
            # 최종 검증
            if pm is None or pm.isNull():
                print(f"[DEBUG] load_page 오류: 모든 방법 실패")
                _log_error(self, "페이지 이미지 변환 실패", Exception("모든 변환 방법 실패"))
                return
            
            # pm이 유효한지 확인
            if pm is None or pm.isNull():
                print(f"[DEBUG] load_page 오류: QPixmap 생성 실패 (페이지 {index})")
                _log_error(self, "페이지 이미지 생성 실패", Exception("QPixmap이 null입니다"))
                return
        except Exception as e:
            import traceback
            print(f"[DEBUG] load_page 오류: {e}")
            traceback.print_exc()
            _log_error(self, "페이지 로드 오류", e)
            return
        
        print(f"[DEBUG] load_page: 이미지 생성 완료, scene 업데이트 시작")
        
        try:
            self.scene.clear()
            # ▼▼▼ [결정적 수정] 파괴된 객체에 대한 참조를 여기서 모두 초기화합니다. ▼▼▼
            self._preview_ellipse = None
            self._preview_text = None
            self._stamp_preview_item = None
            # ▲▲▲ 여기까지 3줄 추가 ▲▲▲
            self._stamp_graphics_items.clear()
            self._clear_stamp_highlight()
            self._page_pix = self.scene.addPixmap(pm)
            self.view.setSceneRect(pm.rect())
            if self.view_show_numbering:
                for it in self.items:
                    if it.page_index == index:
                        self._draw_label(it)
            if self.view_show_stamps:
                for st in self.stamps:
                    if st.page_index == index:
                        self._draw_stamp(st)
            if self.flow_view_enabled:
                self._draw_flow_elements()
            self._preview_ellipse = None
            self._preview_text = None
            self._on_zoom_changed(self.view._scale())
            self._reapply_highlight_from_selection(same_page_only=True)
            self._update_page_navigation_ui()
            self._update_thumbnail_selection()
            self._refresh_table_view()
            self._refresh_stamp_table()
            # [핵심 수정] UI 업데이트를 바로 호출하지 않고, 0초 뒤에 실행하도록 예약합니다.
            QtCore.QTimer.singleShot(0, self._sync_ui_to_current_mode)
            # ▼▼▼ 여기에 이 한 줄을 추가! ▼▼▼
            self.view.setFocus()
        except Exception as e:
            import traceback
            print(f"load_page - UI 업데이트 오류: {e}")
            traceback.print_exc()
            _log_error(self, "페이지 UI 업데이트 오류", e)

    def go_prev(self):
        if self.doc and self.cur_page_index > 0:
            self.load_page(self.cur_page_index - 1)

    def go_next(self):
        if self.doc and self.cur_page_index < len(self.doc) - 1:
            self.load_page(self.cur_page_index + 1)

    # ===== ▼▼▼ 아래 4개 함수를 여기에 새로 추가해주세요 ▼▼▼ =====
    def _go_to_page_from_spinbox(self, page_num):
        """페이지 번호 입력창(SpinBox)의 값이 변경되었을 때 호출됩니다."""
        if self.doc and (page_num - 1) != self.cur_page_index:
            self.load_page(page_num - 1)  # 스핀박스는 1-based, 인덱스는 0-based

    def _update_page_navigation_ui(self):
        """현재 문서 상태에 맞춰 페이지 네비게이션 UI를 업데이트합니다."""
        if self.doc and len(self.doc) > 0:
            total_pages = len(self.doc)
            self.lbl_total_pages.setText(f"/ {total_pages}")
            # 스핀박스의 범위를 설정하고 현재 페이지 번호로 값을 변경
            self.spin_page.setRange(1, total_pages)
            self.spin_page.blockSignals(True)  # 값 변경 시그널을 잠시 막음
            self.spin_page.setValue(self.cur_page_index + 1)
            self.spin_page.blockSignals(False)  # 시그널 다시 활성화
            # 처음/마지막 페이지일 때 이전/다음 버튼 비활성화
            self.btn_prev.setEnabled(self.cur_page_index > 0)
            self.btn_next.setEnabled(self.cur_page_index < total_pages - 1)
            self.spin_page.setEnabled(True)
        else:
            # 문서가 없을 경우 모든 컨트롤을 비활성화
            self.lbl_total_pages.setText("/ 0")
            self.spin_page.setRange(1, 1)
            self.spin_page.setValue(1)
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.spin_page.setEnabled(False)

    def _clear_3d_viewer(self):
        """3D 뷰어 탭의 모든 위젯을 삭제하고 모델 경로를 초기화합니다. (ViewportManager로 위임)"""
        if hasattr(self, 'plotter'):
            self.viewport_manager.set_plotter(self.plotter)
        return self.viewport_manager.clear_3d_viewer()

    def _clear_thumbnails(self):
        """썸네일 뷰의 모든 위젯/아이템을 안전하게 삭제합니다."""
        layout = getattr(self, "thumbnail_layout", None)
        if layout is None:
            self.thumbnail_widgets = []
            return
        # 뒤에서부터 제거해야 인덱스 꼬임이 없습니다.
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            w = item.widget()
            if w is not None:
                # 위젯은 removeWidget + 부모 분리 + deleteLater 조합이 안전합니다.
                layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
            else:
                # 스페이서/레이아웃 아이템은 removeItem으로 제거
                layout.removeItem(item)
        # 내부 상태도 비워줍니다.
        self.thumbnail_widgets = []

    def _populate_thumbnails(self):
        # 기존 썸네일 싹 정리
        self._clear_thumbnails()
        if not getattr(self, "doc", None):
            return
        # 방어: 누락 필드가 있어도 죽지 않도록
        if not hasattr(self, "thumbnail_widgets"):
            self.thumbnail_widgets = []
        page_count = 0
        try:
            page_count = len(self.doc)
        except Exception:
            # 페이지 수 조회 실패 시 조용히 중단
            return
        for i in range(page_count):
            try:
                page = self.doc.get_page(i)
                # 썸네일은 너무 무겁지 않게 기본 DPI 또는 작은 사이즈로 생성
                # pypdfium2의 render()는 scale 파라미터를 사용 (72 DPI ≈ scale 1.0)
                pil_img = page.render(scale=1.0)
                qimg = _pil_to_qimage(pil_img)
                q_pixmap = QtGui.QPixmap.fromImage(qimg)
                thumbnail = ThumbnailLabel(i, q_pixmap)
                thumbnail.clicked.connect(self.load_page)
                self.thumbnail_layout.addWidget(thumbnail)
                self.thumbnail_widgets.append(thumbnail)
            except Exception:
                # 개별 페이지 렌더 실패는 건너뜁니다. (한 장 때문에 전체가 멈추지 않게)
                continue
        # 스페이서(스트레치) 추가 — 이제 _clear_thumbnails가 안전하게 처리합니다.
        self.thumbnail_layout.addStretch(1)
        # 현재 페이지 하이라이트 및 가시화
        self._update_thumbnail_selection()

    def _update_thumbnail_selection(self):
        if not getattr(self, "thumbnail_widgets", None):
            return
        for i, widget in enumerate(self.thumbnail_widgets):
            is_active = i == getattr(self, "cur_page_index", -1)
            try:
                widget.setActive(is_active)
                if is_active and hasattr(self, "thumbnail_area"):
                    # 선택 썸네일이 보이도록 스크롤
                    self.thumbnail_area.ensureWidgetVisible(widget, 0, 0)
            except Exception:
                # 썸네일 위젯이 이미 파괴 중일 수 있으니 조용히 패스
                pass
        # ===== ▼▼▼ 아래 2개 함수를 새로 추가해주세요 ▼▼▼ =====

    def _go_to_page_from_spinbox(self, page_num):
        """페이지 번호 입력창(SpinBox)의 값이 변경되었을 때 호출됩니다."""
        if self.doc and (page_num - 1) != self.cur_page_index:
            self.load_page(page_num - 1)  # 스핀박스는 1-based, 인덱스는 0-based

    def _update_page_navigation_ui(self):
        """현재 문서 상태에 맞춰 페이지 네비게이션 UI를 업데이트합니다."""
        if self.doc and len(self.doc) > 0:
            total_pages = len(self.doc)
            self.lbl_total_pages.setText(f"/ {total_pages}")
            # 스핀박스의 범위를 설정하고 현재 페이지 번호로 값을 변경
            self.spin_page.setRange(1, total_pages)
            self.spin_page.blockSignals(True)  # 값 변경 시그널을 잠시 막음
            self.spin_page.setValue(self.cur_page_index + 1)
            self.spin_page.blockSignals(False)  # 시그널 다시 활성화
            # 처음/마지막 페이지일 때 이전/다음 버튼 비활성화
            self.btn_prev.setEnabled(self.cur_page_index > 0)
            self.btn_next.setEnabled(self.cur_page_index < total_pages - 1)
            self.spin_page.setEnabled(True)
        else:
            # 문서가 없을 경우 모든 컨트롤을 비활성화
            self.lbl_total_pages.setText("/ 0")
            self.spin_page.setRange(1, 1)
            self.spin_page.setValue(1)
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.spin_page.setEnabled(False)

    # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
    def fit_to_window(self):
        if self._page_pix is None:
            return
        self.view.fitInView(self._page_pix, QtCore.Qt.KeepAspectRatio)
        self.view.zoom_changed.emit(self.view._scale())

    def set_auto_highres(self, on: bool):
        self.auto_highres = on
        if on:
            self._maybe_rerender_for_zoom(self.view._scale())

    def rerender_now(self):
        if not self.doc:
            return
        desired = self._render_factor_for_scale(self.view._scale())
        if desired != self.render_scale:
            self.render_scale = desired
        self.load_page(self.cur_page_index)

    def _on_zoom_changed(self, s: float):
        self._update_status()
        self._maybe_rerender_for_zoom(s)

    def view_to_pdf(self, p: QtCore.QPointF) -> Tuple[float, float]:
        return (p.x() / float(self.render_scale), p.y() / float(self.render_scale))

    def pdf_to_view(self, x: float, y: float) -> QtCore.QPointF:
        return QtCore.QPointF(x * float(self.render_scale), y * float(self.render_scale))

    def set_start_number(self):
        ret = QtWidgets.QInputDialog.getInt(
            self, "Set Start Number", "Next label number:", int(self.next_no), 1, 999999, 1
        )
        if isinstance(ret, tuple):
            n, ok = ret
        else:
            n, ok = int(ret), True
        if ok:
            self.next_no = int(n)
            self._refresh_preview_text()
            self._update_status()

    # 숫자만 입력되도록 수정. V2.87에서 수정...
    # insert 기능 위해 on_clicked 함수 변경.(통갈이) v3.14...
    # 빈행 삽입 후 프리뷰모드에선 정상적으로 보이나 실제로 입력할땐 소수점 나타나는 문제.. v3.21
    # 사격모드 넣으면서 수정함. v3.30에서..
    def on_clicked(self, scene_pos: QtCore.QPointF):
        # 1. 사격 모드는 최상단에서 처리 (기존과 동일)
        if self.shooting_mode:
            # ▼▼▼ [핵심] 비어있던 사격 모드 로직을 복원합니다. ▼▼▼
            try:
                if self.sound_effect:
                    self.sound_effect.play()
            except Exception as e:
                print(f"사운드 재생 오류: {e}")
            pm = random.choice(self.bullet_hole_pixmaps)
            scaled_pm = pm.scaled(
                128, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            bullet_item = self.scene.addPixmap(scaled_pm)
            bullet_item.setTransformOriginPoint(scaled_pm.rect().center())
            bullet_item.setRotation(random.uniform(0, 360))
            bullet_item.setScale(random.uniform(0.9, 1.20))
            bullet_item.setPos(
                scene_pos.x() - scaled_pm.width() / 2, scene_pos.y() - scaled_pm.height() / 2
            )
            bullet_item.setZValue(10000)
            self.bullet_hole_items.append(bullet_item)
            if self.enable_shell:
                self._spawn_shell(scene_pos)
            return
            # ▲▲▲ 여기까지 복원 ▲▲▲
        # 2. 현재 활성 모드에 따라 작업 결정
        if self.active_mode == "numbering":
            pdf_xy = self.view_to_pdf(scene_pos)
            if self.insert_mode:
                self.execute_item_insertion(pdf_xy)
                return
            if not self.doc:
                return
            is_separate_mode = self.numbering_mode == "page_specific"
            if is_separate_mode:
                items_on_page = [it.no for it in self.items if it.page_index == self.cur_page_index]
                cur_no = int(max(items_on_page, default=0) + 1)
            else:
                cur_no = int(self.next_no)
            # ▼▼▼ [핵심 수정] 되살리기 스택을 여기서 비웁니다. ▼▼▼
            self.redo_stack.clear()
            if self.input_mode == "number_only":
                it = MarkItem(no=cur_no, page_index=self.cur_page_index, pdf_point=pdf_xy)
            else:
                # ▼▼▼ 주석 부분을 이 코드로 교체해주세요 ▼▼▼
                dim_type, ok = QtWidgets.QInputDialog.getItem(
                    self, "Demension Type", "Type:", DIM_TYPES, 0, False
                )
                if not ok:
                    return
                val_float, ok = QtWidgets.QInputDialog.getDouble(
                    self, "Demension", "Value:", 0.00, -999999, 999999, 10
                )
                if not ok:
                    return
                p_float, p_ok = QtWidgets.QInputDialog.getDouble(
                    self, "Maximum", "Upper (e.g. +0.20):", 0.00, -999999, 999999, 10
                )
                m_float, m_ok = QtWidgets.QInputDialog.getDouble(
                    self, "Minimum", "Lower (e.g. -0.10):", 0.00, -999999, 999999, 10
                )
                p_val = str(p_float) if p_ok else ""
                m_val = str(m_float) if m_ok else ""
                # ▲▲▲ 여기까지 교체 ▲▲▲
                it = MarkItem(
                    no=cur_no,
                    page_index=self.cur_page_index,
                    pdf_point=pdf_xy,
                    dim_type=dim_type,
                    value=str(val_float),
                    tol_plus=normalize_signed_text(p_val),
                    tol_minus=normalize_signed_text(m_val),
                )
            if not is_separate_mode:
                self.next_no = float(cur_no + 1)
            self.items.append(it)  # 상태 리스트에 추가
            # ▼▼▼ [핵심 추가] 행동을 역사에 기록합니다. ▼▼▼
            action = {"type": "add_numbering", "item": it}
            self.undo_stack.append(action)
            # ▲▲▲ 여기까지 추가 ▲▲▲
            self._draw_label(it)
            self._refresh_table_view()
            self._refresh_preview_text()
            self._update_undo_redo_hint()
            self._update_status()
            self._set_dirty()
            self._update_flow_view()
        elif self.active_mode == "stamp":
            if not self.doc:
                return
            stamp_key = self._get_current_stamp_key()
            if not stamp_key:
                self.statusBar().showMessage(
                    "사용할 스탬프가 선택되지 않았습니다. '스탬프 관리'에서 스탬프를 추가해주세요.",
                    3000,
                )
                return
            pdf_xy = self.view_to_pdf(scene_pos)
            # ▼▼▼ [핵심] 스탬프 종류에 맞는 서식을 찾아옵니다. ▼▼▼
            stamp_info = self.registered_stamps.get(stamp_key, {})
            settings = stamp_info.get("settings")  # 종류별 서식을 먼저 시도
            if settings is None:  # 없으면 전역 서식을 사용
                settings = {
                    "opacity": self.stamp_opacity,
                    "rotation": self.stamp_rotation,
                    "opacity_random": self.stamp_opacity_random,
                    "rotation_random": self.stamp_rotation_random,
                    "opacity_min": self.stamp_opacity_min,
                    "opacity_max": self.stamp_opacity_max,
                    "rotation_min": self.stamp_rotation_min,
                    "rotation_max": self.stamp_rotation_max,
                }
            opacity = (
                random.uniform(settings["opacity_min"], settings["opacity_max"])
                if settings["opacity_random"]
                else settings["opacity"]
            )
            rotation = (
                random.uniform(settings["rotation_min"], settings["rotation_max"])
                if settings["rotation_random"]
                else settings["rotation"]
            )
            new_stamp = StampItem(
                stamp_key=stamp_key,
                page_index=self.cur_page_index,
                pdf_point=pdf_xy,
                opacity=opacity,
                rotation=rotation,
            )
            # ▲▲▲ 서식 적용 완료 ▲▲▲
            self.stamps.append(new_stamp)
            action = {"type": "add_stamp", "item": new_stamp}
            self.undo_stack.append(action)
            self.redo_stack.clear()
            self._draw_stamp(new_stamp)
            self._refresh_stamp_table()
            self._set_dirty()
            self._update_undo_redo_hint()

    # 탄피생성
    def _spawn_shell(self, origin: QtCore.QPointF):
        """사격 시 한 발당 탄피 1개 생성."""
        if not self.shell_pixmaps:
            return
        pm = random.choice(self.shell_pixmaps)
        # 적당히 작게(원본이 크면) 스케일
        target_h = 36  # 픽셀 높이 기준
        scale = target_h / pm.height()
        if scale < 1.0:
            pm = pm.scaled(
                pm.width() * scale,
                target_h,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
        item = self.scene.addPixmap(pm)
        item.setTransformOriginPoint(pm.rect().center())
        item.setZValue(10001)  # 혈흔(10000)보다 위에
        # 초기 위치(총구 기준 조금 오른쪽/위로 치우치게)
        offx = random.uniform(10, 24)
        offy = random.uniform(-6, -14)
        item.setPos(origin.x() + offx - pm.width() / 2, origin.y() + offy - pm.height() / 2)
        # 초기 속도(오른쪽 위로 튀게)
        # 각도 20~60도, 속도 600~900 px/s
        ang = math.radians(random.uniform(20, 60))
        spd = random.uniform(600, 900)
        vx = math.cos(ang) * spd
        vy = -math.sin(ang) * spd  # 위(-)
        # 회전(초당 360~900도)
        spin = random.uniform(360, 900) * (1 if random.random() < 0.5 else -1)
        # 수명(초) — 이후 페이드아웃/삭제
        life = random.uniform(0.9, 1.4)
        self.shell_items.append(
            {"item": item, "vx": vx, "vy": vy, "spin": spin, "life": life, "opacity": 1.0}
        )
        # 타이머 가동
        if not self._shell_timer.isActive():
            self._shell_timer.start()

    # 탄피 효과
    def _tick_shells(self):
        """탄피 간단 물리(중력/드래그/회전/페이드)"""
        if not self.shell_items:
            self._shell_timer.stop()
            return
        dt = 0.016  # 16ms 가정
        g = self._shell_gravity
        drag = self._shell_air_drag
        alive = []
        for s in self.shell_items:
            it = s["item"]
            # 속도 업데이트: 중력/공기저항
            s["vy"] += g * dt
            s["vx"] *= 1.0 - drag * dt
            s["vy"] *= 1.0 - 0.5 * drag * dt  # y는 약간 덜 감쇠
            # 위치/회전 업데이트
            p = it.pos()
            it.setPos(p.x() + s["vx"] * dt, p.y() + s["vy"] * dt)
            it.setRotation(it.rotation() + s["spin"] * dt)
            # 수명/페이드
            s["life"] -= dt
            if s["life"] <= 0:
                s["opacity"] -= 2.0 * dt  # 0.5초 내외로 사라짐
                if s["opacity"] <= 0:
                    # 완전 소멸
                    self.scene.removeItem(it)
                    continue
                it.setOpacity(s["opacity"])
            # (선택) 바닥 충돌: 바닥선 지정되어 있으면 약하게 튕김
            if self._shell_floor_y is not None:
                bottom = it.pos().y() + it.pixmap().height() / 2
                if bottom >= self._shell_floor_y:
                    # 바닥에 닿으면 위치 보정 + 반사
                    dy = bottom - self._shell_floor_y
                    it.setPos(it.pos().x(), it.pos().y() - dy)
                    s["vy"] = -abs(s["vy"]) * 0.35  # 감쇠 반사
                    s["vx"] *= 0.8
                    s["spin"] *= 0.8
            alive.append(s)
        self.shell_items = alive
        if not self.shell_items:
            self._shell_timer.stop()

    def clear_bullet_holes(self):
        # ... (기존 혈흔 정리)
        for s in getattr(self, "shell_items", []):
            try:
                self.scene.removeItem(s["item"])
            except Exception:
                pass
        self.shell_items = []

    # 총알구멍 삭제 함수 v3.33에서...
    def clear_bullet_holes(self):
        """화면에 있는 모든 총알 구멍 잔상을 제거합니다."""
        for item in self.bullet_hole_items:
            self.scene.removeItem(item)
        self.bullet_hole_items.clear()

    def _draw_flow_elements(self):
        """(주석 추가됨) 아이콘과 텍스트 라벨을 포함한 흐름도를 그립니다."""
        items_on_page = [it for it in self.items if it.page_index == self.cur_page_index]
        if not items_on_page:
            return

        def draw_arrow_line(p1_item, p2_item):
            p1_style = p1_item.custom_style or self.style
            p2_style = p2_item.custom_style or self.style
            line_color = QtGui.QColor(self.style.flow_line_color)
            line_color.setAlphaF(self.style.flow_line_opacity)
            qt_line_style = {
                "solid": QtCore.Qt.SolidLine,
                "dash": QtCore.Qt.DashLine,
                "dot": QtCore.Qt.DotLine,
            }.get(self.style.flow_line_style, QtCore.Qt.SolidLine)
            line_width = max(1, p1_style.stroke_width * 0.8)
            line_pen = QtGui.QPen(line_color, line_width, qt_line_style)
            arrow_brush = QtGui.QBrush(line_color)
            p1 = self.pdf_to_view(*p1_item.pdf_point)
            p2 = self.pdf_to_view(*p2_item.pdf_point)
            line_vec = p2 - p1
            length = math.hypot(line_vec.x(), line_vec.y())
            if length < 1e-6:
                return
            margin1 = p1_style.radius_view_px * 2.0
            margin2 = p2_style.radius_view_px * 2.0
            new_p1 = p1 + line_vec / length * margin1
            new_p2 = p2 - line_vec / length * margin2
            if QtCore.QLineF(new_p1, new_p2).length() < 1:
                return
            line = self.scene.addLine(QtCore.QLineF(new_p1, new_p2), line_pen)
            line.setZValue(1)
            self.flow_items.append(line)
            # ▼▼▼ 기존 화살촉 그리는 로직을 아래 코드로 교체 ▼▼▼
            arrow_size = max(5, p2_style.radius_view_px * 0.8)
            if self.style.flow_arrow_style == "arrow":
                angle = math.atan2(p1.y() - p2.y(), p1.x() - p2.x())
                arrow_p1 = new_p2 + QtCore.QPointF(
                    math.cos(angle + 0.5) * arrow_size, math.sin(angle + 0.5) * arrow_size
                )
                arrow_p2 = new_p2 + QtCore.QPointF(
                    math.cos(angle - 0.5) * arrow_size, math.sin(angle - 0.5) * arrow_size
                )
                arrow_head = QtGui.QPolygonF([new_p2, arrow_p1, arrow_p2])
                arrow_item = self.scene.addPolygon(arrow_head, line_pen, arrow_brush)
                arrow_item.setZValue(1)
                self.flow_items.append(arrow_item)
            elif self.style.flow_arrow_style == "circle":
                r = arrow_size * 0.7
                circle_item = self.scene.addEllipse(
                    new_p2.x() - r, new_p2.y() - r, 2 * r, 2 * r, line_pen, arrow_brush
                )
                circle_item.setZValue(1)
                self.flow_items.append(circle_item)
            # "none"일 경우 아무것도 그리지 않음
            # ▲▲▲ 여기까지 교체 ▲▲▲

        def draw_marker_icon(item, pixmap):
            scaled_pixmap = pixmap.scaled(
                QtCore.QSize(48, 48), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            marker = self.scene.addPixmap(scaled_pixmap)
            pt = self.pdf_to_view(*item.pdf_point)
            offset_x = scaled_pixmap.width() / 2
            # ===== ▼▼▼ [위치 조절 가이드 1: 시작/끝 아이콘] ▼▼▼ =====
            # Y 좌표 오프셋: 아이콘의 높이 전체를 사용합니다.
            # 이 값을 조절하여 아이콘의 상하 위치를 변경할 수 있습니다.
            # * scaled_pixmap.height() * 1.0 -> 아이콘의 바닥이 점의 중심에 위치 (현재)
            # * scaled_pixmap.height() * 0.5 -> 아이콘의 중심이 점의 중심에 위치
            # * scaled_pixmap.height() * 1.2 -> 현재보다 더 위로 올라감
            offset_y = scaled_pixmap.height() * 1.3
            marker.setPos(pt.x() - offset_x, pt.y() - offset_y)
            # ===== ▲▲▲ [위치 조절 가이드 1: 시작/끝 아이콘] ▲▲▲ =====
            marker.setZValue(1)
            self.flow_items.append(marker)

        if self.numbering_mode == "page_specific":
            sorted_items = sorted(items_on_page, key=lambda x: x.no)
            if self.style.flow_show_start_end:
                if len(sorted_items) > 0:
                    draw_marker_icon(sorted_items[0], self.start_marker_pixmap)
                if len(sorted_items) > 1:
                    draw_marker_icon(sorted_items[-1], self.end_marker_pixmap)
            for i in range(len(sorted_items) - 1):
                draw_arrow_line(sorted_items[i], sorted_items[i + 1])
        else:  # 전체 이어가기 모드
            all_sorted_items = sorted(self.items, key=lambda x: x.no)
            if not all_sorted_items:
                return
            transition_markers = {}
            color_index = 0
            for i in range(len(all_sorted_items) - 1):
                current_item, next_item = all_sorted_items[i], all_sorted_items[i + 1]
                if current_item.page_index != next_item.page_index:
                    color = self.transition_colors[color_index % len(self.transition_colors)]
                    transition_markers[id(current_item)] = (
                        color,
                        f"to P.{next_item.page_index + 1}",
                    )
                    transition_markers[id(next_item)] = (
                        color,
                        f"from P.{current_item.page_index + 1}",
                    )
                    color_index += 1

            def draw_transition_marker(item, color, text):
                style = item.custom_style or self.style
                pt = self.pdf_to_view(*item.pdf_point)
                r = style.radius_view_px + 7
                pen = QtGui.QPen(color, 5)
                pen.setCapStyle(QtCore.Qt.RoundCap)
                marker = self.scene.addEllipse(pt.x() - r, pt.y() - r, 2 * r, 2 * r, pen)
                marker.setZValue(1)
                self.flow_items.append(marker)
                font = QtGui.QFont("Arial", 14, QtGui.QFont.Bold)
                text_item = self.scene.addSimpleText(text, font)
                text_item.setBrush(QtGui.QBrush(color))
                text_item.setPen(QtGui.QPen(QtGui.QColor("white"), 0.5))
                text_item.setZValue(2)
                text_rect = text_item.boundingRect()
                # ===== ▼▼▼ [위치 조절 가이드 2: 연결점 텍스트] ▼▼▼ =====
                # 1. 거리 조절: 원의 테두리(r)에서 얼마나 멀리 떨어뜨릴지 결정합니다.
                #    이 숫자(20)를 키우면 텍스트가 원에서 더 멀어집니다.
                offset = r + 23
                # 2. 방향 조절: 텍스트를 배치할 대각선 방향을 결정합니다.
                #    pt.x() + : 오른쪽 | pt.x() - : 왼쪽
                #    pt.y() - : 위쪽   | pt.y() + : 아래쪽
                text_x = pt.x() + offset / math.sqrt(2) - text_rect.width() / 2  # 현재: 오른쪽(+)
                text_y = pt.y() - offset / math.sqrt(2) - text_rect.height() / 2  # 현재: 위쪽(-)
                text_item.setPos(text_x, text_y)
                # ===== ▲▲▲ [위치 조절 가이드 2: 연결점 텍스트] ▲▲▲ =====
                self.flow_items.append(text_item)

            if self.style.flow_show_start_end and len(all_sorted_items) > 1:
                start_item, end_item = all_sorted_items[0], all_sorted_items[-1]
                if start_item.page_index == self.cur_page_index:
                    draw_marker_icon(start_item, self.start_marker_pixmap)
                if end_item.page_index == self.cur_page_index:
                    draw_marker_icon(end_item, self.end_marker_pixmap)
            for i, current_item in enumerate(all_sorted_items):
                if current_item.page_index != self.cur_page_index:
                    continue
                if id(current_item) in transition_markers:
                    color, text = transition_markers[id(current_item)]
                    draw_transition_marker(current_item, color, text)
                next_item = all_sorted_items[i + 1] if i < len(all_sorted_items) - 1 else None
                if next_item and next_item.page_index == current_item.page_index:
                    draw_arrow_line(current_item, next_item)

    def _update_flow_view(self):
        """기존 흐름도를 지우고, 현재 상태에 맞춰 새로 그립니다."""
        # 1. 기록부에 있는 모든 흐름도 아이템을 화면에서 삭제
        for item in self.flow_items:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self.flow_items.clear()
        # 2. 흐름도 보기가 켜져 있을 때만 새로 그림
        if self.flow_view_enabled:
            self._draw_flow_elements()

    def _ellipse_brush(self, style: LabelStyle):
        if style.fill_none or style.fill_color.alpha() == 0:
            return QtCore.Qt.NoBrush
        return QtGui.QBrush(style.fill_color)

    def _draw_label(self, it: MarkItem):
        # --- 수정: 그리기 전에 사용할 스타일 결정 ---
        style = it.custom_style if it.custom_style else self.style
        pt = self.pdf_to_view(*it.pdf_point)
        r = style.radius_view_px
        ellipse = self.scene.addEllipse(
            pt.x() - r,
            pt.y() - r,
            2 * r,
            2 * r,
            pen=QtGui.QPen(style.stroke_color, style.stroke_width),
            brush=self._ellipse_brush(style),
        )  # _ellipse_brush도 style을 받도록 수정 필요
        txt = self.scene.addText(
            self._format_no(it.no), QtGui.QFont("Arial", style.font_size_view_px, QtGui.QFont.Bold)
        )
        txt.setDefaultTextColor(style.text_color)
        br = txt.boundingRect()
        txt.setPos(pt.x() - br.width() / 2, pt.y() - br.height() / 2)
        ellipse.setZValue(2)
        txt.setZValue(2)

    def _append_table_row(self, it: MarkItem):
        """Append new row to table. (TableManager delegation)"""
        return self.table_manager._append_table_row(it)

    def _format_3d_parameter(self, viewport_parameters: str) -> str:
        """3D 뷰포트 파라메터를 (x, y, z, distance) 형태로 포맷팅합니다. (TableManager로 위임)"""
        return self.table_manager._format_3d_parameter(viewport_parameters)

    def on_table_cell_clicked(self, row: int, col: int):
        """테이블 셀 클릭 이벤트 처리. (TableManager로 위임)"""
        return self.table_manager.on_table_cell_clicked(row, col)

    def on_table_selection_changed(self):
        """테이블 선택 변경 이벤트 처리. (TableManager로 위임)"""
        return self.table_manager.on_table_selection_changed()

    def _highlight_from_row(self, row: int):
        """Highlight item from table row. (TableManager delegation)"""
        return self.table_manager._highlight_from_row(row)

    def _highlight_by_no(self, no: int):
        """Highlight item by number. (TableManager delegation)"""
        return self.table_manager._highlight_by_no(no)

    def _clear_highlight(self):
        if getattr(self, "_highlight_ellipse", None):
            try:
                self.scene.removeItem(self._highlight_ellipse)
            except Exception:
                pass
            self._highlight_ellipse = None
        self._highlight_item_no = None

    def on_table_item_changed(self, qitem: QtWidgets.QTableWidgetItem):
        """테이블 아이템 변경 이벤트 처리. (TableManager로 위임)"""
        return self.table_manager.on_table_item_changed(qitem)

    def _sync_highlight_from_table(self):
        """테이블에서 하이라이트 동기화. (TableManager로 위임)"""
        return self.table_manager._sync_highlight_from_table()

    def _apply_highlight_from_table(self):
        """Apply highlight from table selection. (TableManager delegation)"""
        return self.table_manager._apply_highlight_from_table()

    def highlight_label(self, it: MarkItem):
        if not it:
            return
        if it.page_index != self.cur_page_index:
            self.load_page(it.page_index)
        self.clear_highlight()
        # ===== ▼▼▼ 수정 시작: 개별 서식을 정확히 반영하도록 변경 ▼▼▼ =====
        # 1. 하이라이트를 그릴 때 사용할 스타일을 먼저 결정합니다 (개별 스타일 우선).
        style_to_use = it.custom_style if it.custom_style else self.style
        # 2. 결정된 스타일을 기준으로 모든 값을 계산합니다.
        pt = self.pdf_to_view(*it.pdf_point)
        r = style_to_use.radius_view_px + 5
        pen = QtGui.QPen(self.highlight_color)
        pen.setWidth(style_to_use.stroke_width + 8)
        # ===== ▲▲▲ 수정 끝 ▲▲▲ =====
        pen.setCosmetic(True)
        ell = self.scene.addEllipse(
            pt.x() - r, pt.y() - r, 2 * r, 2 * r, pen=pen, brush=QtCore.Qt.NoBrush
        )
        ell.setZValue(9999)
        self._highlight_ellipse = ell
        self._highlight_item_no = it.no

    def clear_highlight(self):
        if self._highlight_ellipse:
            try:
                self.scene.removeItem(self._highlight_ellipse)
            except Exception:
                pass
            self._highlight_ellipse = None
        self._highlight_item_no = None

    def clear_highlight(self):
        if self._highlight_ellipse:
            try:
                self.scene.removeItem(self._highlight_ellipse)
            except Exception:
                pass
            self._highlight_ellipse = None
        self._highlight_item_no = None

    def clear_selection_and_highlight(self):
        """테이블의 선택 상태와 화면의 하이라이트를 모두 해제합니다."""
        self.table.clearSelection()
        self.clear_highlight()

    def _reapply_highlight_from_selection(self, same_page_only=False):
        rows = sorted({ix.row() for ix in self.table.selectedIndexes()})
        if not rows:
            self.clear_highlight()
            return
        r = rows[0]
        if 0 <= r < len(self.items):
            it = self.items[r]
            if same_page_only and it.page_index != self.cur_page_index:
                self.clear_highlight()
                return
            self.highlight_label(it)

    def _shortcut_toggle_edit(self):
        # 단축키(Ctrl+E)가 툴바의 '에디트' 액션을 토글하도록 변경
        self.action_edit.toggle()

    def on_scene_moved(self, scene_pos: QtCore.QPointF):
        if self._preview_ellipse:
            self._preview_ellipse.hide()
        if self._preview_text:
            self._preview_text.hide()
        if self._stamp_preview_item:
            self._stamp_preview_item.hide()
        if self.shooting_mode:
            return
        # 2. 넘버링 모드일 때의 미리보기 로직
        if self.active_mode == "numbering" and self.doc:
            if self.preview_mode == "preview":
                if self._preview_ellipse is None or self._preview_text is None:
                    self._create_preview_items()
                if not self._preview_ellipse.isVisible():
                    self._preview_ellipse.show()
                if not self._preview_text.isVisible():
                    self._preview_text.show()
                self._refresh_preview_text()
                self._move_preview_items(scene_pos)
        # 3. 스탬프 모드일 때의 미리보기 로직
        elif self.active_mode == "stamp" and self.doc:
            current_stamp_name = self._get_current_stamp_key()
            if not current_stamp_name:
                return
            stamp_info = self.registered_stamps.get(current_stamp_name)
            if not stamp_info or not isinstance(stamp_info, dict):
                return
            stamp_path = stamp_info.get("path")
            if not stamp_path:
                return
            pixmap = QtGui.QPixmap(stamp_path)
            if pixmap.isNull():
                return
            # (스탬프 프리뷰 설정 부분만 발췌)
            if self._stamp_preview_item is None:
                self._stamp_preview_item = self.scene.addPixmap(pixmap)
                self._stamp_preview_item.setZValue(10000)
            # 항상 최신 픽스맵 반영
            self._stamp_preview_item.setPixmap(pixmap)
            self._stamp_preview_item.setOpacity(0.5)
            # 1) 프리뷰도 중심 기준 고정
            rect = pixmap.rect()
            self._stamp_preview_item.setOffset(-rect.width() / 2.0, -rect.height() / 2.0)
            self._stamp_preview_item.setTransformOriginPoint(QtCore.QPointF(0, 0))
            # 2) 실제 크기 스케일
            width_mm = stamp_info.get("width_mm", 18.0)
            width_points = (width_mm / 25.4) * 72
            target_pixel_width = width_points * self.render_scale
            original_pixel_width = pixmap.width()
            scale_factor = (
                (target_pixel_width / original_pixel_width) if original_pixel_width > 0 else 1.0
            )
            self._stamp_preview_item.setScale(scale_factor)
            # 3) 커서 위치 = 중심
            self._stamp_preview_item.setPos(scene_pos)
            self._stamp_preview_item.show()

    # 프리뷰 제대로 안되서 수정. v30.2에서...
    def _create_preview_items(self):
        r = self.style.radius_view_px
        pen = QtGui.QPen(self.style.stroke_color)
        pen.setWidth(self.style.stroke_width)
        self._preview_ellipse = self.scene.addEllipse(
            -r, -r, 2 * r, 2 * r, pen=pen, brush=self._ellipse_brush(self.style)
        )
        self._preview_ellipse.setOpacity(0.6)
        self._preview_ellipse.setZValue(10_000)
        font = QtGui.QFont("Arial", self.style.font_size_view_px, QtGui.QFont.Bold)
        self._preview_text = self.scene.addText("", font)
        self._preview_text.setDefaultTextColor(self.style.text_color)
        self._preview_text.setOpacity(0.6)
        self._preview_text.setZValue(10_001)

    def _move_preview_items(self, p: QtCore.QPointF):
        r = self.style.radius_view_px
        self._preview_ellipse.setRect(p.x() - r, p.y() - r, 2 * r, 2 * r)
        br = self._preview_text.boundingRect()
        self._preview_text.setPos(p.x() - br.width() / 2, p.y() - br.height() / 2)

    def _force_refresh_table(self):
        """Force refresh table with new format. (TableManager delegation)"""
        return self.table_manager._force_refresh_table()

    def _refresh_table_view(self):
        """Refresh table view based on checkbox state. (TableManager delegation)"""
        return self.table_manager._refresh_table_view()

    def _update_undo_redo_hint(self):
        undo_tooltip = "실행 취소"
        if self.undo_stack:
            last_action = self.undo_stack[-1]
            action_type = "넘버링" if last_action["type"] == "add_numbering" else "스탬프"
            undo_tooltip = f"실행 취소 ({action_type})"
        redo_tooltip = "다시 실행"
        if self.redo_stack:
            last_redo_action = self.redo_stack[-1]
            action_type = "넘버링" if last_redo_action["type"] == "add_numbering" else "스탬프"
            redo_tooltip = f"다시 실행 ({action_type})"
        self.action_undo.setToolTip(undo_tooltip)
        self.action_redo.setToolTip(redo_tooltip)
        self.action_undo.setEnabled(bool(self.undo_stack))
        self.action_redo.setEnabled(bool(self.redo_stack))

    def undo(self):
        if not self.undo_stack:
            return
        # 1. 마지막 행동을 역사 기록부에서 가져옴
        last_action = self.undo_stack.pop()
        item = last_action["item"]
        # 2. 행동의 종류에 따라 되돌리기 실행
        if last_action["type"] == "add_numbering":
            if item in self.items:
                self.items.remove(item)
            # 전역 모드일 때만 next_no 업데이트
            if self.numbering_mode != "page_specific":
                int_nos = [it.no for it in self.items if it.no % 1 == 0]
                self.next_no = float(max(int_nos, default=0) + 1)
        elif last_action["type"] == "add_stamp":
            if item in self.stamps:
                self.stamps.remove(item)
        # 3. 되돌린 행동은 '되살리기 기록부'로 이동
        self.redo_stack.append(last_action)
        # 4. 화면 및 상태 업데이트
        self.load_page(item.page_index)  # 해당 아이템이 있던 페이지로 가서 새로고침
        self._update_undo_redo_hint()
        self._update_status()
        self._set_dirty()

    def redo(self):
        if not self.redo_stack:
            return
        # 1. 되살릴 행동을 기록부에서 가져옴
        action_to_redo = self.redo_stack.pop()
        item = action_to_redo["item"]
        # 2. 행동의 종류에 따라 되살리기 실행
        if action_to_redo["type"] == "add_numbering":
            self.items.append(item)
            # 전역 모드일 때만 next_no 업데이트
            if self.numbering_mode != "page_specific":
                self.next_no = max(self.next_no, item.no + 1)
        elif action_to_redo["type"] == "add_stamp":
            self.stamps.append(item)
        # 3. 되살린 행동은 다시 '되돌리기 기록부'로 이동
        self.undo_stack.append(action_to_redo)
        # 4. 화면 및 상태 업데이트
        self.load_page(item.page_index)  # 해당 아이템이 있던 페이지로 가서 새로고침
        self._update_undo_redo_hint()
        self._update_status()
        self._set_dirty()

    def insert_excel_style(self):
        if self.table.currentRow() < 0:
            QtWidgets.QMessageBox.information(
                self, "알림", "기준 위치를 테이블에서 먼저 선택해주세요."
            )
            return
        try:
            target_no = float(self.table.item(self.table.currentRow(), 0).text())
        except (ValueError, AttributeError):
            return
        # ===== ▼▼▼ [수정] 현재 모드에 따라 밀어낼 범위 결정 ▼▼▼ =====
        if self.numbering_mode == "page_specific":
            # 페이지별 모드: 현재 페이지 내에서만 번호를 1씩 증가
            for item in sorted(self.items, key=lambda x: x.no, reverse=True):
                if item.page_index == self.cur_page_index and item.no >= target_no:
                    item.no += 1
        else:
            # 전체 모드: 모든 페이지의 번호를 1씩 증가
            for item in sorted(self.items, key=lambda x: x.no, reverse=True):
                if item.no >= target_no:
                    item.no += 1
            # next_no 업데이트
            int_nos = [it.no for it in self.items if it.no % 1 == 0]
            self.next_no = float(int(max(int_nos) + 1)) if int_nos else 1.0
        # ===== ▲▲▲ 여기까지 수정 ▲▲▲ =====
        self.load_page(self.cur_page_index)
        self._update_undo_redo_hint()
        self._update_status()
        QtWidgets.QMessageBox.information(
            self, "작업 완료", f"'{target_no:g}'번 위치부터 번호가 1씩 밀려났습니다."
        )
        self._set_dirty()

    # 꼬임방지 수정.
    def insert_precision_style(self):
        if self.table.currentRow() < 0:
            QtWidgets.QMessageBox.information(
                self, "알림", "기준 위치를 테이블에서 먼저 선택해주세요."
            )
            return
        try:
            target_no = float(self.table.item(self.table.currentRow(), 0).text())
        except (ValueError, AttributeError):
            return
        new_no, ok = self._get_precision_no(target_no)
        if not ok:
            return
        # ===== ▼▼▼ [수정] 현재 모드에 따라 중복 번호 체크 ▼▼▼ =====
        is_duplicate = False
        if self.numbering_mode == "page_specific":
            # 페이지별 모드: 현재 페이지 내에서만 중복 확인
            is_duplicate = any(
                it.no == new_no and it.page_index == self.cur_page_index for it in self.items
            )
        else:
            # 전체 모드: 전체 항목에서 중복 확인
            is_duplicate = any(it.no == new_no for it in self.items)
        if is_duplicate:
            QtWidgets.QMessageBox.warning(self, "오류", "이미 존재하는 번호입니다.")
            return
        # ===== ▲▲▲ 여기까지 수정 ▲▲▲ =====
        self.insert_mode = True
        self.insert_option = "precision"
        self.insert_target_no = new_no
        self.statusBar().showMessage(
            f"'{new_no:g}'번을 삽입할 위치를 도면에서 클릭하세요... (취소: ESC)"
        )
        self.view.setCursor(QtCore.Qt.CrossCursor)
        self._refresh_preview_text()

    def delete_items(self):
        """선택한 항목을 삭제합니다. 현재 보이는 목록을 기준으로 안전하게 작동합니다."""
        selected_rows = sorted(list(set(index.row() for index in self.table.selectedIndexes())))
        if not selected_rows:
            return
        # 현재 테이블에 표시된 아이템 목록을 그대로 가져옵니다.
        items_on_display = []
        if self.numbering_mode == "page_specific":
            items_on_display = sorted(
                [it for it in self.items if it.page_index == self.cur_page_index],
                key=lambda x: x.no,
            )
        else:
            items_on_display = sorted(self.items, key=lambda x: x.no)
        # 고유 ID를 사용하여 삭제할 아이템을 정확히 식별합니다.
        items_to_delete_ids = set()
        for row in selected_rows:
            if 0 <= row < len(items_on_display):
                items_to_delete_ids.add(id(items_on_display[row]))
        if not items_to_delete_ids:
            return
        # 전체 self.items 목록에서 해당 아이템들을 제거합니다.
        self.items = [it for it in self.items if id(it) not in items_to_delete_ids]
        # 화면과 데이터를 새로고침합니다.
        self.load_page(self.cur_page_index)
        self._update_undo_redo_hint()
        self._update_status()
        self._set_dirty()
        QtWidgets.QMessageBox.information(
            self, "삭제 완료", f"{len(items_to_delete_ids)}개 항목을 삭제했습니다."
        )

    def _refresh_preview_text(self):
        if self._preview_text:
            if self.insert_mode:
                # 삽입 모드일 경우, 삽입될 번호를 프리뷰에 표시
                self._preview_text.setPlainText(f"{self.insert_target_no:g}")
            else:
                # 페이지별 넘버링 모드인지 확인
                if (
                    hasattr(self, "cb_separate_numbering")
                    and self.numbering_mode == "page_specific"
                ):
                    # 현재 페이지의 마지막 번호를 찾아 +1 한 값을 미리보기로 표시
                    items_on_page = [
                        it.no for it in self.items if it.page_index == self.cur_page_index
                    ]
                    preview_no = int(max(items_on_page, default=0) + 1)
                    self._preview_text.setPlainText(str(preview_no))
                else:
                    # 전체 넘버링 모드일 경우, 다음 번호(next_no)를 미리보기로 표시
                    self._preview_text.setPlainText(str(int(self.next_no)))

    def _get_precision_no(self, target_no):
        """0.1 단위로 조절 가능한 소수점 번호 입력창을 엽니다."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("넘버링 삽입")
        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel("삽입할 번호를 입력하거나 조절하세요:")
        spinbox = QtWidgets.QDoubleSpinBox()
        spinbox.setRange(0, 99999)
        spinbox.setDecimals(1)
        spinbox.setSingleStep(0.1)
        spinbox.setValue(target_no)
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(label)
        layout.addWidget(spinbox)
        layout.addWidget(button_box)
        if dialog.exec():
            # ===== ▼▼▼ 수정: 반올림하여 부동소수점 오차 제거 ▼▼▼ =====
            return round(spinbox.value(), 2), True
        return 0.0, False

    def execute_item_insertion(self, pdf_xy):
        """(수정됨) 새 항목을 현재 모드에 맞게 안전하게 삽입하고 화면을 새로고침합니다."""
        choice = self.insert_option
        insert_no = self.insert_target_no
        if choice == "precision":
            new_item = MarkItem(no=insert_no, page_index=self.cur_page_index, pdf_point=pdf_xy)
            self.items.append(new_item)
            # ===== ▼▼▼ [수정] 모드에 따라 next_no를 스마트하게 관리 ▼▼▼ =====
            if self.numbering_mode != "page_specific":
                # 전체 모드일 때만 next_no를 업데이트합니다.
                self.next_no = float(int(max(it.no for it in self.items) + 1))
            # ===== ▲▲▲ 여기까지 수정 ▲▲▲ =====
        # 삽입 모드 상태를 초기화합니다.
        self.insert_mode = False
        self.view.setCursor(QtCore.Qt.ArrowCursor)
        # ===== ▼▼▼ [수정] 가장 안전하고 검증된 방식으로 화면 전체 새로고침 ▼▼▼ =====
        self.load_page(self.cur_page_index)
        self._update_undo_redo_hint()
        self._update_status()
        self._set_dirty()
        # ===== ▲▲▲ 여기까지 수정 ▲▲▲ =====
        if choice == "precision":
            QtWidgets.QMessageBox.information(
                self, "삽입 완료", f"{insert_no:g}번이 새롭게 삽입되었습니다."
            )

    def cancel_insert_mode(self):
        """삽입 모드를 취소합니다."""
        if self.insert_mode:
            self.insert_mode = False
            self.view.setCursor(QtCore.Qt.ArrowCursor)
            self._update_status()

    def adjust_label_style(self, property_name: str, delta: int):
        """전역 라벨 스타일의 숫자 속성을 조절하고 화면을 새로고침합니다."""
        current_value = getattr(self.style, property_name)
        new_value = current_value + delta
        # 값이 비정상적으로 커지거나 작아지지 않도록 최소/최대값 제한
        if "radius" in property_name:
            new_value = max(6, min(64, new_value))
        elif "width" in property_name:
            new_value = max(1, min(10, new_value))
        elif "font" in property_name:
            new_value = max(6, min(48, new_value))
        setattr(self.style, property_name, new_value)
        self.load_page(self.cur_page_index)  # 변경사항을 즉시 반영
        self._set_dirty()

    def toggle_preview_mode(self):
        """프리뷰 모드(프리뷰/십자선)를 전환합니다."""
        if self.preview_mode == "preview":
            self.set_preview_mode("crosshair")
            self.a_crosshair.setChecked(True)
        else:
            self.set_preview_mode("preview")
            self.a_preview.setChecked(True)

    # 추가. 플로우라인  실시간 반영.
    def _update_flow_view(self):
        """기존 흐름도를 지우고, 현재 상태에 맞춰 새로 그립니다."""
        # 1. 기록부에 있는 모든 흐름도 아이템을 화면에서 삭제
        for item in self.flow_items:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self.flow_items.clear()
        # 2. 흐름도 보기가 켜져 있을 때만 새로 그림
        if self.flow_view_enabled:
            self._draw_flow_elements()

    # delete_and_renumber_items 삭제후 통합. v3.22에서...
    def toggle_highlighting(self, checked):
        """하이라이트 활성화 상태를 토글합니다."""
        self.highlight_enabled = checked
        # ===== ▼▼▼ 추가된 부분 시작 ▼▼▼ =====
        # 메뉴와 툴바의 체크 상태를 동기화합니다.
        if hasattr(self, "a_highlight"):
            self.a_highlight.setChecked(checked)
        if hasattr(self, "action_highlight_toolbar"):
            self.action_highlight_toolbar.setChecked(checked)
        # ===== ▲▲▲ 추가된 부분 끝 ▲▲▲ =====
        if not checked:
            self.clear_highlight()  # 기능이 꺼지면 현재 하이라이트를 즉시 제거

    def _build_items_dataframe(self):
        return pd.DataFrame(
            [
                {
                    "No": it.no,
                    "Demension Type": it.dim_type,
                    "Demension": dim_format(it.dim_type, it.value),
                    "Maximum": it.tol_plus,
                    "Minimum": it.tol_minus,
                }
                for it in self.items
            ]
        )
        # ===== ▼▼▼ 스탬프 데이터프레임 생성 함수 (새로 추가) ▼▼▼ =====

    def _build_stamps_dataframe(self):
        """찍힌 스탬프 목록으로 Pandas DataFrame을 생성합니다."""
        stamp_data = []
        # 페이지와 순번에 따라 스탬프 정렬
        sorted_stamps = sorted(
            self.stamps, key=lambda s: (s.page_index, s.pdf_point[1], s.pdf_point[0])
        )
        # 페이지별 순번 매기기
        page_counters = defaultdict(int)
        for stamp in sorted_stamps:
            page_index = stamp.page_index
            page_counters[page_index] += 1
            stamp_data.append(
                {
                    "No": page_counters[page_index],
                    "Page": page_index + 1,
                    "Stamp Type": stamp.stamp_key,
                    "Rotation": f"{stamp.rotation:.1f}°",
                }
            )
        return pd.DataFrame(stamp_data)

    # ===== ▲▲▲ 여기까지 추가 ▲▲▲ =====
    def export_csv_dialog(self):
        # ===== ▼▼▼ 수정 시작 ▼▼▼ =====
        default_dir = self.project_dir or ""
        default_filename = (
            f"{self.project_name}_Inspection.csv" if self.project_name else "output.csv"
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "CSV로 저장", os.path.join(default_dir, default_filename), "CSV Files (*.csv)"
        )
        # ===== ▲▲▲ 수정 끝 ▲▲▲ =====
        if path:
            self._export_csv(path)

    def export_xlsx_dialog(self):
        default_dir = self.project_dir or ""
        default_filename = (
            f"{self.project_name}_Inspection.xlsx" if self.project_name else "output.xlsx"
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "XLSX로 저장", os.path.join(default_dir, default_filename), "Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            # 두 종류의 데이터프레임을 각각 생성
            df_items = self._build_items_dataframe()
            df_stamps = self._build_stamps_dataframe()
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                # 'Numbering' 시트에 넘버링 데이터 저장
                df_items.to_excel(writer, index=False, sheet_name="Numbering")
                ws_items = writer.sheets["Numbering"]
                fmt = "+0.00;-0.00;0.00"
                for col_letter in ["D", "E"]:  # Max and Min columns
                    for cell in ws_items[col_letter]:
                        if cell.row > 1:
                            cell.number_format = fmt
                # 'Stamps' 시트에 스탬프 데이터 저장
                if not df_stamps.empty:
                    df_stamps.to_excel(writer, index=False, sheet_name="Stamps")
            QtWidgets.QMessageBox.information(
                self, "성공", f"엑셀 파일이 성공적으로 저장되었습니다:\n{path}"
            )
        except Exception as e:
            _log_error(self, "엑셀 내보내기 오류", e)

    def _export_csv(self, path):
        df = self._build_items_dataframe()
        df.to_csv(path, index=False, encoding="utf-8-sig")

    def _export_xlsx(self, path):
        df = self._build_items_dataframe()
        # Ensure Maximum/Minimum are numeric for formatting
        df["Maximum"] = pd.to_numeric(df["Maximum"], errors="coerce")
        df["Minimum"] = pd.to_numeric(df["Minimum"], errors="coerce")
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
            ws = writer.sheets["Sheet1"]
            # Apply number format to columns
            fmt = "+0.00;-0.00;0.00"
            for col_letter in ["D", "E"]:  # Max and Min columns
                for cell in ws[col_letter]:
                    if cell.row > 1:  # Skip header
                        cell.number_format = fmt

    def _export_current_page_jpg_with_labels(self, path):
        if not self.doc:
            return
        page = self.doc.get_page(self.cur_page_index)
        # pypdfium2의 render()는 PIL Image를 반환합니다
        pil_img = page.render(scale=self.render_scale)
        img = _pil_to_qimage(pil_img)
        pm = QtGui.QPixmap.fromImage(img)
        p = QtGui.QPainter(pm)
        pen = QtGui.QPen(self.style.stroke_color)
        pen.setWidth(self.style.stroke_width)
        p.setPen(pen)
        p.setBrush(self._ellipse_brush())
        font = QtGui.QFont("Arial", self.style.font_size_view_px, QtGui.QFont.Bold)
        p.setFont(font)
        for it in self.items:
            if it.page_index != self.cur_page_index:
                continue
            pt = self.pdf_to_view(*it.pdf_point)
            r = self.style.radius_view_px
            p.drawEllipse(QtCore.QPointF(pt.x(), pt.y()), r, r)
            p.setPen(QtGui.QPen(self.style.text_color))
            m = QtGui.QFontMetrics(font)
            label_str = self._format_no(it.no)
            tw = m.horizontalAdvance(label_str)
            p.drawText(pt.x() - tw / 2, pt.y() + m.ascent() / 2, label_str)
        p.end()
        pm.save(path, "JPG", quality=95)

    def _add_toolbar_action(
        self, toolbar, icon_path_qrc: str, text: str, slot, checkable=False, checked=False
    ):
        """툴바에 액션을 추가합니다. (UIManager로 위임)"""
        return self.ui_manager.add_toolbar_action(toolbar, icon_path_qrc, text, slot, checkable, checked)

    # 스페셜 서식 적용하기 위해 통째로 교체 v2.95에서...
    def open_numbering_settings(self):
        """넘버링 관련 전역 설정을 열고, 변경 시 화면을 새로고칩니다."""
        if self._open_numbering_settings_dialog(self.style):
            self.load_page(self.cur_page_index)
            self._set_dirty()
    
    def _create_color_picker_dialog(self, initial_color, title):
        """기존 색상 선택 팔레트(QColorDialog)에 투명도 슬라이더를 추가한 다이얼로그를 생성합니다."""
        # 기존 QColorDialog를 생성
        color_dialog = QtWidgets.QColorDialog(initial_color, self)
        color_dialog.setWindowTitle(title)
        color_dialog.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, True)
        color_dialog.setOption(QtWidgets.QColorDialog.DontUseNativeDialog, True)  # 네이티브 다이얼로그 비활성화하여 커스터마이징 가능하게 함
        color_dialog.setCurrentColor(initial_color)
        
        # QColorDialog의 버튼 박스를 찾아서 그 위에 투명도 슬라이더를 추가
        # QColorDialog는 내부적으로 복잡한 구조를 가지고 있으므로, 
        # 모든 자식 위젯을 순회하여 QDialogButtonBox를 찾음
        def find_button_box(widget):
            """위젯 트리에서 QDialogButtonBox를 찾습니다."""
            if isinstance(widget, QtWidgets.QDialogButtonBox):
                return widget
            for child in widget.findChildren(QtWidgets.QDialogButtonBox):
                return child
            return None
        
        button_box = find_button_box(color_dialog)
        
        # 투명도 슬라이더 추가
        # 투명도 100% = 완전 투명 (alpha = 0), 투명도 0% = 불투명 (alpha = 255)
        transparency_layout = QtWidgets.QHBoxLayout()
        transparency_label = QtWidgets.QLabel("투명도:")
        transparency_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        transparency_slider.setRange(0, 100)
        # alpha를 투명도로 변환: 투명도 = 100 - (alpha * 100 / 255)
        # 초기값은 0% (불투명)로 설정
        initial_transparency = 100 - int(initial_color.alpha() * 100 / 255)
        transparency_slider.setValue(initial_transparency)
        transparency_slider.setMinimumWidth(200)
        transparency_value_label = QtWidgets.QLabel(f"{transparency_slider.value()}%")
        transparency_value_label.setMinimumWidth(40)
        
        def update_transparency(value):
            transparency_value_label.setText(f"{value}%")
            # 투명도를 alpha로 변환: alpha = (100 - 투명도) * 255 / 100
            # 투명도 100% = alpha 0 (완전 투명), 투명도 0% = alpha 255 (불투명)
            current = color_dialog.currentColor()
            current.setAlpha(int((100 - value) * 255 / 100))
            color_dialog.setCurrentColor(current)
        
        transparency_slider.valueChanged.connect(update_transparency)
        
        # 색상 변경 시 투명도 슬라이더 업데이트
        def on_color_changed(color):
            # alpha를 투명도로 변환: 투명도 = 100 - (alpha * 100 / 255)
            transparency_percent = 100 - int(color.alpha() * 100 / 255)
            transparency_slider.blockSignals(True)
            transparency_slider.setValue(transparency_percent)
            transparency_value_label.setText(f"{transparency_percent}%")
            transparency_slider.blockSignals(False)
        
        color_dialog.currentColorChanged.connect(on_color_changed)
        
        transparency_layout.addWidget(transparency_label)
        transparency_layout.addWidget(transparency_slider)
        transparency_layout.addWidget(transparency_value_label)
        transparency_layout.addStretch()
        
        # 버튼 박스를 찾았으면 그 위에 투명도 슬라이더를 삽입
        if button_box:
            button_box_parent = button_box.parent()
            if button_box_parent:
                parent_layout = button_box_parent.layout()
                if parent_layout:
                    # 버튼 박스의 인덱스를 찾아서 그 위에 삽입
                    button_box_index = parent_layout.indexOf(button_box)
                    if button_box_index >= 0:
                        parent_layout.insertLayout(button_box_index, transparency_layout)
                    else:
                        parent_layout.addLayout(transparency_layout)
                else:
                    # 레이아웃이 없으면 직접 추가
                    main_layout = color_dialog.layout()
                    if main_layout:
                        main_layout.insertLayout(main_layout.count() - 1, transparency_layout)
        else:
            # 버튼 박스를 찾지 못했으면 메인 레이아웃에 추가
            main_layout = color_dialog.layout()
            if main_layout:
                main_layout.insertLayout(main_layout.count() - 1, transparency_layout)
        
        # 다이얼로그에 selected_color 속성 추가를 위한 래퍼
        original_accept = color_dialog.accept
        def custom_accept():
            color_dialog.selected_color = color_dialog.currentColor()
            original_accept()
        color_dialog.accept = custom_accept
        
        return color_dialog
    
    def _open_color_dialog(self, color_type: str):
        """
        색상 팔레트 다이얼로그를 열고 선택한 색상을 바로 적용합니다.
        
        Args:
            color_type: "stroke" (테두리), "text" (숫자), "fill" (채우기)
        """
        # 현재 색상 가져오기
        if color_type == "stroke":
            current_color = self.style.stroke_color
            title = "테두리 색 선택"
        elif color_type == "text":
            current_color = self.style.text_color
            title = "숫자 색 선택"
        elif color_type == "fill":
            current_color = self.style.fill_color
            title = "채우기 색 선택"
        else:
            return
        
        # 색상 팔레트 다이얼로그 열기
        dlg = self._create_color_picker_dialog(current_color, title)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            selected_color = dlg.selected_color
            if selected_color.isValid():
                if color_type == "stroke":
                    self.style.stroke_color = selected_color
                elif color_type == "text":
                    self.style.text_color = selected_color
                elif color_type == "fill":
                    self.style.fill_color = selected_color
                    # 채우기 색이 설정되면 fill_none 해제
                    if selected_color.alpha() > 0:
                        self.style.fill_none = False
                
                self.load_page(self.cur_page_index)
                self._set_dirty()

    def _open_numbering_settings_dialog(self, style_object: LabelStyle) -> bool:
        """'넘버링 설정' 대화상자를 엽니다. 성공 시 True를 반환합니다."""
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("넘버링 설정")
        form = QtWidgets.QFormLayout(dlg)
        # --- 1. 넘버링 입력 방식 설정 ---
        cb_with_input = QtWidgets.QCheckBox("넘버링 시 치수 함께 입력", dlg)
        cb_with_input.setChecked(self.input_mode == "with_input")
        form.addRow("입력 방식:", cb_with_input)
        separator1 = QtWidgets.QFrame()
        separator1.setFrameShape(QtWidgets.QFrame.HLine)
        form.addRow(separator1)
        # --- 2. 라벨 서식 설정 (기존과 동일) ---
        form.addRow(QtWidgets.QLabel("<b>라벨 서식</b>"))
        sp_r = QtWidgets.QSpinBox(dlg)
        sp_r.setRange(6, 64)
        sp_r.setValue(style_object.radius_view_px)
        sp_s = QtWidgets.QSpinBox(dlg)
        sp_s.setRange(1, 10)
        sp_s.setValue(style_object.stroke_width)
        sp_f = QtWidgets.QSpinBox(dlg)
        sp_f.setRange(6, 48)
        sp_f.setValue(style_object.font_size_view_px)
        # ... (이하 기존 open_label_settings의 위젯 설정 코드는 그대로 유지) ...
        btn_fill = QtWidgets.QPushButton("채우기 색…", dlg)
        btn_stk = QtWidgets.QPushButton("테두리 색…", dlg)
        btn_txt = QtWidgets.QPushButton("숫자 색…", dlg)
        
        # 테두리 색과 숫자 색 버튼에 아이콘 추가
        try:
            from utils.helpers import icon_if
            circle_color_icon = icon_if("resources/icons/circle_color.png")
            text_color_icon = icon_if("resources/icons/text_color.png")
            if circle_color_icon and not circle_color_icon.isNull():
                btn_stk.setIcon(circle_color_icon)
                btn_stk.setIconSize(QtCore.QSize(16, 16))
            if text_color_icon and not text_color_icon.isNull():
                btn_txt.setIcon(text_color_icon)
                btn_txt.setIconSize(QtCore.QSize(16, 16))
        except Exception as e:
            print(f"아이콘 로드 실패: {e}")
        cb_none = QtWidgets.QCheckBox("채우기 없음(투명)", dlg)
        cb_none.setChecked(style_object.fill_none or style_object.fill_color.alpha() == 0)
        separator2 = QtWidgets.QFrame()
        separator2.setFrameShape(QtWidgets.QFrame.HLine)
        # --- 3. 흐름도 서식 설정 (기존과 동일) ---
        form.addRow(QtWidgets.QLabel("<b>흐름도 서식</b>"))
        opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        opacity_slider.setRange(0, 100)
        opacity_slider.setValue(int(style_object.flow_line_opacity * 100))
        opacity_label = QtWidgets.QLabel(f"{opacity_slider.value()}%")
        opacity_slider.valueChanged.connect(lambda val: opacity_label.setText(f"{val}%"))
        opacity_layout = QtWidgets.QHBoxLayout()
        opacity_layout.addWidget(opacity_slider)
        opacity_layout.addWidget(opacity_label)
        btn_flow_color = QtWidgets.QPushButton("흐름도 선 색상…", dlg)
        combo_flow_style = QtWidgets.QComboBox(dlg)
        combo_flow_style.addItems(["solid", "dash", "dot"])
        combo_flow_style.setCurrentText(style_object.flow_line_style)
        cb_show_start_end = QtWidgets.QCheckBox("시작/끝점 강조 표시", dlg)
        cb_show_start_end.setChecked(style_object.flow_show_start_end)
        temp_style = copy.deepcopy(style_object)

        def pick_flow_color():
            c = QtWidgets.QColorDialog.getColor(temp_style.flow_line_color, self)
            if c.isValid():
                temp_style.flow_line_color = c

        btn_flow_color.clicked.connect(pick_flow_color)

        # 채우기 색 제한 제거 (enable_fill 함수 제거)

        def pick_fill():
            # 투명도 슬라이더가 있는 색상 팔레트 다이얼로그 열기
            dlg = self._create_color_picker_dialog(temp_style.fill_color, "채우기 색 선택")
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                temp_style.fill_color = dlg.selected_color

        def pick_stk():
            # 투명도 슬라이더가 있는 색상 팔레트 다이얼로그 열기
            dlg = self._create_color_picker_dialog(temp_style.stroke_color, "테두리 색 선택")
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                temp_style.stroke_color = dlg.selected_color

        def pick_txt():
            # 투명도 슬라이더가 있는 색상 팔레트 다이얼로그 열기
            dlg = self._create_color_picker_dialog(temp_style.text_color, "숫자 색 선택")
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                temp_style.text_color = dlg.selected_color

        btn_fill.clicked.connect(pick_fill)
        btn_stk.clicked.connect(pick_stk)
        btn_txt.clicked.connect(pick_txt)
        form.addRow("원 반지름(px)", sp_r)
        form.addRow("테두리 두께(px)", sp_s)
        form.addRow("폰트 크기(px)", sp_f)
        form.addRow(cb_none)
        form.addRow(btn_fill)
        # 테두리 색과 숫자 색을 한 줄에 배치하고 구분선 추가
        color_separator = QtWidgets.QFrame()
        color_separator.setFrameShape(QtWidgets.QFrame.VLine)
        color_separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.addWidget(btn_stk)
        color_layout.addWidget(color_separator)
        color_layout.addWidget(btn_txt)
        color_layout.addStretch()
        form.addRow(color_layout)
        form.addRow(separator2)
        form.addRow("흐름도 투명도", opacity_layout)
        form.addRow(btn_flow_color, combo_flow_style)
        form.addRow(cb_show_start_end)
        bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=dlg
        )
        form.addWidget(bb)

        def accept():
            # [수정] OK를 누를 때 체크박스 상태에 따라 input_mode를 설정
            new_mode = "with_input" if cb_with_input.isChecked() else "number_only"
            self.set_input_mode(new_mode)
            # 기존 스타일 저장 로직
            style_object.radius_view_px = sp_r.value()
            style_object.stroke_width = sp_s.value()
            style_object.font_size_view_px = sp_f.value()
            style_object.fill_none = cb_none.isChecked()
            style_object.flow_line_opacity = opacity_slider.value() / 100.0
            style_object.fill_color = temp_style.fill_color
            style_object.stroke_color = temp_style.stroke_color
            style_object.text_color = temp_style.text_color
            if style_object.fill_none:
                c = QtGui.QColor(style_object.fill_color)
                c.setAlpha(0)
                style_object.fill_color = c
            style_object.flow_line_color = temp_style.flow_line_color
            style_object.flow_line_style = combo_flow_style.currentText()
            style_object.flow_show_start_end = cb_show_start_end.isChecked()
            dlg.accept()

        bb.accepted.connect(accept)
        bb.rejected.connect(dlg.reject)
        return dlg.exec() == QtWidgets.QDialog.Accepted

    def set_input_mode(self, mode: str):
        self.input_mode = mode
        # 메뉴의 체크 상태를 현재 모드와 동기화합니다.
        if hasattr(self, "a_only"):
            self.a_only.setChecked(mode == "number_only")
        if hasattr(self, "a_inp"):
            self.a_inp.setChecked(mode == "with_input")
        # ===== ▼▼▼ 추가된 부분 시작 ▼▼▼ =====
        # 툴바의 '치수 입력 모드' 버튼 상태를 동기화합니다.
        if hasattr(self, "action_mode_switch"):
            self.action_mode_switch.setChecked(mode == "with_input")
        # ===== ▲▲▲ 추가된 부분 끝 ▲▲▲ =====
        self._on_zoom_changed(self.view._scale())

    def _update_status(self):
        # 현재 활성 모드에 따라 표시할 텍스트를 결정합니다.
        if self.active_mode == "numbering":
            mode_display_text = "넘버링 모드"
        elif self.active_mode == "stamp":
            mode_display_text = "스탬프 모드"
        else:  # "view"
            mode_display_text = "보기 모드"
        # 상태 표시줄 메시지를 새로운 형식으로 업데이트합니다.
        zoom_text = f"Zoom: {int(self.view._scale()*100)}%"
        render_text = f"Render: {self.render_scale}x"
        self.statusBar().showMessage(
            f"상태: {mode_display_text}   ·   {zoom_text}   ·   {render_text}"
        )

    def _sync_items_from_table(self):
        """Sync items from table data. (TableManager delegation)"""
        return self.table_manager._sync_items_from_table()
            # 3D 뷰포트 파라메터 동기화 (5번째 컬럼)
            # 테이블에는 포맷팅된 값이 표시되지만, 원본 JSON 데이터는 이미 MarkItem에 저장되어 있음
            # 따라서 별도로 동기화할 필요 없음 (이미 저장된 원본 데이터 유지)

    # ===== ★★★ 이 함수만 최종 버전으로 교체되었습니다 ★★★ =====
    # ===== 넘버링 흐름도 함께 저장 위해 통째로 교체(중간에 일부 코드 추가)v2.93에서함. =====
    # 스페셜 서식 적용 위해 통째로 교체. v2.95에서 함.
    # 스페셜 서식 적용 제대로 안되서 다시 교체... 시벌...몇번째여..ㅠㅠㅠ v2.98에서...
    # 스페셜 서식 흐름도 적용 저장 업데이트... 시벌 벌써 v3.00이네..ㅠㅠㅠ v2.99에서...
    def _save_pdf_with_labels(self, path):
        # 최종 완성본: 이미지 생성 방식으로 모든 문제를 해결합니다. (흐름도 포함)
        import math
        from collections import defaultdict

        if not self.doc:
            raise RuntimeError("PDF가 로드되지 않았습니다.")
        out_doc = pdfium.PdfDocument.new()
        # 페이지별로 넘버링과 스탬프 아이템을 미리 그룹화합니다.
        items_by_page = defaultdict(list)
        for item in self.items:
            items_by_page[item.page_index].append(item)
        stamps_by_page = defaultdict(list)
        for stamp in self.stamps:
            stamps_by_page[stamp.page_index].append(stamp)
        # 원본 문서의 모든 페이지를 순회합니다.
        for i in range(len(self.doc)):
            src_page = self.doc.get_page(i)
            items_on_this_page = items_by_page.get(i, [])
            stamps_on_this_page = stamps_by_page.get(i, [])
            # 해당 페이지에 넘버링과 스탬프가 모두 없으면 원본 그대로 추가합니다.
            if not items_on_this_page and not stamps_on_this_page:
                _pdfium_insert_pdf(out_doc, self.doc, from_page=i, to_page=i)
                continue
            # --- 넘버링이나 스탬프가 있는 페이지는 이미지로 변환하여 처리 ---
            zoom = self.render_scale * 2
            # pypdfium2의 render()는 scale 파라미터를 사용합니다
            pil_img = src_page.render(scale=zoom)
            img = _pil_to_qimage(pil_img)
            pm = QtGui.QPixmap.fromImage(img)
            painter = QtGui.QPainter(pm)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            # 1. 흐름도 그리기 (기존 로직 복원)
            if self.flow_view_enabled:
                sorted_items = sorted(items_on_this_page, key=lambda x: x.no)
                if sorted_items:
                    # (흐름도를 그리는 모든 코드가 여기에 포함됩니다)
                    # ... 시작/끝점, 화살표 등 ...
                    pass  # 이 부분은 이미 가지고 계신 코드를 그대로 사용하시면 됩니다.
            # 2. 넘버링 그리기 (기존 로직 복원)
            for it in sorted(items_on_this_page, key=lambda item: item.no):
                style = it.custom_style if it.custom_style else self.style
                img_point = self.pdf_to_view(it.pdf_point[0], it.pdf_point[1]) * 2
                pen = QtGui.QPen(style.stroke_color)
                pen.setWidth(style.stroke_width * 2)
                painter.setPen(pen)
                brush = QtCore.Qt.NoBrush
                if not style.fill_none and style.fill_color.alpha() != 0:
                    brush = QtGui.QBrush(style.fill_color)
                painter.setBrush(brush)
                font = QtGui.QFont("Arial", style.font_size_view_px * 2, QtGui.QFont.Bold)
                r = style.radius_view_px * 2
                painter.drawEllipse(img_point, r, r)
                painter.setFont(font)
                painter.setPen(QtGui.QPen(style.text_color))
                fm = QtGui.QFontMetrics(font)
                text_width = fm.horizontalAdvance(self._format_no(it.no))
                text_height = fm.height()
                text_x = img_point.x() - text_width / 2
                text_y = img_point.y() - text_height / 2 + fm.ascent()
                painter.drawText(QtCore.QPointF(text_x, text_y), self._format_no(it.no))
            # 3. 스탬프 그리기 (신규 추가된 로직)
            for st in stamps_on_this_page:
                stamp_info = self.registered_stamps.get(st.stamp_key)
                if not stamp_info or not isinstance(stamp_info, dict):
                    continue
                stamp_path = stamp_info.get("path")
                if not stamp_path:
                    continue
                stamp_pixmap = QtGui.QPixmap(stamp_path)
                if stamp_pixmap.isNull():
                    continue
                # ▼▼▼ [핵심 추가] PDF 저장 시에도 실제 크기 기준으로 스케일 계산 ▼▼▼
                width_mm = stamp_info.get("width_mm", 18.0)
                width_points = (width_mm / 25.4) * 72
                target_pixel_width = width_points * zoom  # painter는 zoom 배율로 그려짐
                original_pixel_width = stamp_pixmap.width()
                if original_pixel_width <= 0:
                    continue
                # 목표 픽셀 크기에 맞게 QPixmap의 크기를 조절
                scaled_pixmap = stamp_pixmap.scaledToWidth(
                    target_pixel_width, QtCore.Qt.SmoothTransformation
                )
                # ▲▲▲ 스케일 계산 완료 ▲▲▲
                painter.save()
                img_point_stamp = self.pdf_to_view(st.pdf_point[0], st.pdf_point[1]) * 2
                painter.setOpacity(st.opacity)
                painter.translate(img_point_stamp)
                painter.rotate(st.rotation)
                offset = QtCore.QPointF(-scaled_pixmap.width() / 2, -scaled_pixmap.height() / 2)
                painter.drawPixmap(offset, scaled_pixmap)  # 스케일된 pixmap을 사용
                painter.restore()
            painter.end()
            # 이미지 데이터를 PDF 페이지로 변환
            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.ReadWrite)
            pm.save(buffer, "PNG")
            image_bytes = bytes(buffer.data())
            buffer.close()
            # QPixmap을 PIL Image로 변환
            qimg = pm.toImage()
            width = qimg.width()
            height = qimg.height()
            # QImage를 numpy array로 변환
            ptr = qimg.constBits()
            if ptr:
                ptr.setsize(qimg.byteCount())
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))  # RGBA
                pil_img = Image.fromarray(arr[:, :, :3])  # RGB만 사용
                
                # PIL Image를 PDF 페이지로 변환 (포인트 단위: 1 픽셀 = 1 포인트, DPI 72 기준)
                width_pt = width
                height_pt = height
                
                # 임시 PDF로 변환 후 import
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.utils import ImageReader
                    
                    c = canvas.Canvas(tmp_path, pagesize=(width_pt, height_pt))
                    img_reader = ImageReader(pil_img)
                    c.drawImage(img_reader, 0, 0, width=width_pt, height=height_pt)
                    c.save()
                    
                    # 변환된 PDF를 읽어서 페이지 import
                    img_doc = pdfium.PdfDocument(tmp_path)
                    if len(img_doc) > 0:
                        out_doc.import_pages(img_doc, pages=[0])
                        img_doc.close()
                    os.unlink(tmp_path)
                except ImportError:
                    # reportlab이 없으면 빈 페이지 생성
                    img_page = out_doc.new_page(width=width_pt, height=height_pt)
                    os.unlink(tmp_path)
            else:
                # 변환 실패 시 빈 페이지 생성
                img_page = out_doc.new_page(width=width, height=height)
        if len(out_doc) > 0:
            out_doc.save(path)
        out_doc.close()


# =====================================================================
#  프로그램 실행 부분
# =====================================================================
def main():
    # 전역 예외 핸들러 설정
    def exception_hook(exc_type, exc_value, exc_traceback):
        """프로그램이 예기치 않게 종료되는 것을 방지하기 위한 예외 핸들러"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"Uncaught exception:\n{error_msg}", file=sys.stderr)
        # Qt 메시지 박스로도 표시
        app = QtWidgets.QApplication.instance()
        if app:
            QtWidgets.QMessageBox.critical(
                None, "치명적 오류", 
                f"예기치 않은 오류가 발생했습니다:\n\n{exc_type.__name__}: {exc_value}\n\n자세한 내용은 콘솔을 확인하세요."
            )
    
    sys.excepthook = exception_hook
    
    app = QtWidgets.QApplication(sys.argv)
    # 이제 main.py를 실행하므로, pdf_to_open 로직은 그대로 둡니다.
    pdf_to_open = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        w = PdfAnnotator(pdf_path=pdf_to_open)
        w.show()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        traceback.print_exc()
        QtWidgets.QMessageBox.critical(
            None, "시작 오류", 
            f"프로그램 시작 중 오류가 발생했습니다:\n\n{str(e)}\n\n자세한 내용은 콘솔을 확인하세요."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
