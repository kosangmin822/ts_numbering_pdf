# ui/dialogs.py

import os
import copy
import json
import pandas as pd
from PySide6 import QtWidgets, QtCore, QtGui
from utils.helpers import resource_path
from ui.styles import GLOBAL_STYLESHEET

class NewProjectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, default_name="", default_dir=""):
        super().__init__(parent)
        self.setWindowTitle("새 프로젝트 생성")
        self.setMinimumWidth(500)
        self.setMinimumHeight(250)
        self.project_name = ""
        self.project_dir = ""
        
        # 메인 레이아웃
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # 제목
        title_label = QtWidgets.QLabel("새 프로젝트 생성")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #09090B;")
        main_layout.addWidget(title_label)
        
        # 입력 폼
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(16)
        form_layout.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        
        # 프로젝트 이름
        name_label = QtWidgets.QLabel("프로젝트 이름:")
        name_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("예: PJT-2025-09-21")
        self.name_edit.setText(default_name)
        form_layout.addRow(name_label, self.name_edit)
        
        # 작업 폴더
        dir_label = QtWidgets.QLabel("작업 폴더:")
        dir_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        dir_layout = QtWidgets.QHBoxLayout()
        dir_layout.setSpacing(8)
        self.dir_edit = QtWidgets.QLineEdit()
        self.dir_edit.setReadOnly(True)
        self.dir_edit.setText(default_dir)
        self.dir_button = QtWidgets.QPushButton("폴더 선택...")
        self.dir_button.setProperty("buttonStyle", "secondary")
        self.dir_button.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.dir_edit, 1)
        dir_layout.addWidget(self.dir_button)
        form_layout.addRow(dir_label, dir_layout)
        
        main_layout.addLayout(form_layout)
        main_layout.addStretch()
        
        # 버튼
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()
        
        cancel_button = QtWidgets.QPushButton("취소")
        cancel_button.setProperty("buttonStyle", "secondary")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QtWidgets.QPushButton("생성")
        ok_button.setMinimumWidth(100)
        ok_button.clicked.connect(self.validate_and_accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        main_layout.addLayout(button_layout)
    def select_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "작업 폴더를 선택하세요")
        if directory:
            self.dir_edit.setText(directory)
    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        directory = self.dir_edit.text()
        if not name:
            QtWidgets.QMessageBox.warning(self, "입력 오류", "프로젝트 이름을 입력해야 합니다.")
            return
        if not directory:
            QtWidgets.QMessageBox.warning(self, "입력 오류", "작업 폴더를 선택해야 합니다.")
            return
        self.project_name = name
        self.project_dir = directory
        self.accept()

class InsertDialog(QtWidgets.QDialog):
    def __init__(self, target_no, parent=None):
        super().__init__(parent)
        self.setWindowTitle("새 항목 삽입")
        self.setMinimumWidth(480)
        self.choice = "excel"
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 제목
        title_label = QtWidgets.QLabel("새 항목 삽입")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #09090B;")
        layout.addWidget(title_label)
        
        # 설명
        desc_label = QtWidgets.QLabel(f"<b>{target_no:g}번</b> 위치에 새 항목을 삽입합니다.<br>방식을 선택해주세요.")
        desc_label.setStyleSheet("font-size: 14px; color: #71717A; margin-bottom: 8px;")
        layout.addWidget(desc_label)
        
        # 옵션 그룹
        options_group = QtWidgets.QGroupBox()
        options_group.setStyleSheet("QGroupBox { border: none; padding: 0; margin: 0; }")
        options_layout = QtWidgets.QVBoxLayout(options_group)
        options_layout.setSpacing(12)
        
        self.radio_excel = QtWidgets.QRadioButton("빈 행 삽입 (Excel 방식)")
        self.radio_excel.setToolTip("새로운 정수 번호를 삽입하고, 기존 번호들을 뒤로 밀어냅니다.")
        self.radio_excel.setChecked(True)
        self.radio_excel.toggled.connect(lambda: self.set_choice("excel"))
        
        self.radio_precision = QtWidgets.QRadioButton("소수점 번호 삽입 (정밀 방식)")
        self.radio_precision.setToolTip("기존 번호는 유지하고, 8.5, 9.1과 같은 소수점 번호를 삽입합니다.")
        self.radio_precision.toggled.connect(lambda: self.set_choice("precision"))
        
        options_layout.addWidget(self.radio_excel)
        options_layout.addWidget(self.radio_precision)
        layout.addWidget(options_group)
        
        layout.addStretch()
        
        # 버튼
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()
        
        cancel_button = QtWidgets.QPushButton("취소")
        cancel_button.setProperty("buttonStyle", "secondary")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QtWidgets.QPushButton("삽입")
        ok_button.setMinimumWidth(100)
        ok_button.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
    def set_choice(self, choice):
        self.choice = choice
    @staticmethod
    def get_insert_choice(target_no, parent=None):
        dialog = InsertDialog(target_no, parent)
        if dialog.exec():
            return dialog.choice
        return None

class AppendPdfDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF 가져오기 방식 선택")
        self.setMinimumWidth(450)
        self.choice = None
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 제목
        title_label = QtWidgets.QLabel("PDF 가져오기")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #09090B;")
        layout.addWidget(title_label)
        
        # 설명
        label = QtWidgets.QLabel("이미 열려있는 PDF 문서가 있습니다.\n작업 방식을 선택해주세요.")
        label.setStyleSheet("font-size: 14px; color: #71717A; margin-bottom: 8px;")
        layout.addWidget(label)
        
        # 버튼들
        btn_replace = QtWidgets.QPushButton("새로 불러오기 (기존 작업 닫기)")
        btn_replace.setProperty("buttonStyle", "secondary")
        btn_replace.setMinimumHeight(48)
        btn_replace.clicked.connect(self.select_replace)
        layout.addWidget(btn_replace)
        
        btn_append = QtWidgets.QPushButton("뒤에 이어붙이기")
        btn_append.setMinimumHeight(48)
        btn_append.clicked.connect(self.select_append)
        layout.addWidget(btn_append)
    def select_replace(self):
        self.choice = "replace"
        self.accept()
    def select_append(self):
        self.choice = "append"
        self.accept()

class StampSettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("스탬프 설정")
        self.setMinimumWidth(500)
        self.settings = {
            "opacity": 1.0, "rotation": 0.0,
            "opacity_random": True, "rotation_random": True,
            "opacity_min": 0.9, "opacity_max": 1.0,
            "rotation_min": -5.0, "rotation_max": 5.0
        }
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # 제목
        title_label = QtWidgets.QLabel("스탬프 설정")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #09090B;")
        main_layout.addWidget(title_label)
        
        # 투명도 그룹
        opacity_group = QtWidgets.QGroupBox("투명도 (Opacity)")
        opacity_layout = QtWidgets.QVBoxLayout(opacity_group)
        opacity_layout.setSpacing(12)
        
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_label = QtWidgets.QLabel("100%")
        self.opacity_label.setStyleSheet("min-width: 50px; font-weight: 500;")
        
        fixed_opacity_layout = QtWidgets.QHBoxLayout()
        fixed_opacity_layout.addWidget(QtWidgets.QLabel("고정 값:"))
        fixed_opacity_layout.addWidget(self.opacity_slider, 1)
        fixed_opacity_layout.addWidget(self.opacity_label)
        
        self.opacity_random_cb = QtWidgets.QCheckBox("랜덤 범위 사용")
        self.opacity_min_spin = QtWidgets.QDoubleSpinBox()
        self.opacity_min_spin.setRange(0.0, 1.0)
        self.opacity_min_spin.setSingleStep(0.01)
        self.opacity_max_spin = QtWidgets.QDoubleSpinBox()
        self.opacity_max_spin.setRange(0.0, 1.0)
        self.opacity_max_spin.setSingleStep(0.01)
        
        random_opacity_layout = QtWidgets.QHBoxLayout()
        random_opacity_layout.addWidget(QtWidgets.QLabel("범위:"))
        random_opacity_layout.addWidget(self.opacity_min_spin, 1)
        random_opacity_layout.addWidget(QtWidgets.QLabel("~"))
        random_opacity_layout.addWidget(self.opacity_max_spin, 1)
        
        opacity_layout.addLayout(fixed_opacity_layout)
        opacity_layout.addWidget(self.opacity_random_cb)
        opacity_layout.addLayout(random_opacity_layout)
        main_layout.addWidget(opacity_group)
        
        # 회전 그룹
        rotation_group = QtWidgets.QGroupBox("회전 (Rotation)")
        rotation_layout = QtWidgets.QVBoxLayout(rotation_group)
        rotation_layout.setSpacing(12)
        
        self.rotation_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.rotation_slider.setRange(-180, 180)
        self.rotation_label = QtWidgets.QLabel("0°")
        self.rotation_label.setStyleSheet("min-width: 50px; font-weight: 500;")
        
        fixed_rotation_layout = QtWidgets.QHBoxLayout()
        fixed_rotation_layout.addWidget(QtWidgets.QLabel("고정 값:"))
        fixed_rotation_layout.addWidget(self.rotation_slider, 1)
        fixed_rotation_layout.addWidget(self.rotation_label)
        
        self.rotation_random_cb = QtWidgets.QCheckBox("랜덤 범위 사용")
        self.rotation_min_spin = QtWidgets.QDoubleSpinBox()
        self.rotation_min_spin.setRange(-360, 360)
        self.rotation_min_spin.setSingleStep(0.1)
        self.rotation_max_spin = QtWidgets.QDoubleSpinBox()
        self.rotation_max_spin.setRange(-360, 360)
        self.rotation_max_spin.setSingleStep(0.1)
        
        random_rotation_layout = QtWidgets.QHBoxLayout()
        random_rotation_layout.addWidget(QtWidgets.QLabel("범위:"))
        random_rotation_layout.addWidget(self.rotation_min_spin, 1)
        random_rotation_layout.addWidget(QtWidgets.QLabel("~"))
        random_rotation_layout.addWidget(self.rotation_max_spin, 1)
        
        rotation_layout.addLayout(fixed_rotation_layout)
        rotation_layout.addWidget(self.rotation_random_cb)
        rotation_layout.addLayout(random_rotation_layout)
        main_layout.addWidget(rotation_group)
        
        main_layout.addStretch()
        
        # 버튼
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()
        
        cancel_button = QtWidgets.QPushButton("취소")
        cancel_button.setProperty("buttonStyle", "secondary")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QtWidgets.QPushButton("저장")
        ok_button.setMinimumWidth(100)
        ok_button.clicked.connect(self.accept_settings)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        main_layout.addLayout(button_layout)
        
        # 시그널 연결
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        self.rotation_slider.valueChanged.connect(lambda v: self.rotation_label.setText(f"{v}°"))
        self.opacity_random_cb.toggled.connect(self.update_ui_state)
        self.rotation_random_cb.toggled.connect(self.update_ui_state)
    def set_settings(self, settings: dict):
        self.settings = settings.copy()
        self.opacity_slider.setValue(int(self.settings.get("opacity", 1.0) * 100))
        self.rotation_slider.setValue(int(self.settings.get("rotation", 0.0)))
        self.opacity_random_cb.setChecked(self.settings.get("opacity_random", True))
        self.rotation_random_cb.setChecked(self.settings.get("rotation_random", True))
        self.opacity_min_spin.setValue(self.settings.get("opacity_min", 0.9))
        self.opacity_max_spin.setValue(self.settings.get("opacity_max", 1.0))
        self.rotation_min_spin.setValue(self.settings.get("rotation_min", -5.0))
        self.rotation_max_spin.setValue(self.settings.get("rotation_max", 5.0))
        self.update_ui_state()
    def update_ui_state(self):
        is_opacity_random = self.opacity_random_cb.isChecked()
        self.opacity_slider.setDisabled(is_opacity_random)
        self.opacity_min_spin.setEnabled(is_opacity_random)
        self.opacity_max_spin.setEnabled(is_opacity_random)
        is_rotation_random = self.rotation_random_cb.isChecked()
        self.rotation_slider.setDisabled(is_rotation_random)
        self.rotation_min_spin.setEnabled(is_rotation_random)
        self.rotation_max_spin.setEnabled(is_rotation_random)
    def accept_settings(self):
        self.settings["opacity"] = self.opacity_slider.value() / 100.0
        self.settings["rotation"] = float(self.rotation_slider.value())
        self.settings["opacity_random"] = self.opacity_random_cb.isChecked()
        self.settings["rotation_random"] = self.rotation_random_cb.isChecked()
        self.settings["opacity_min"] = self.opacity_min_spin.value()
        self.settings["opacity_max"] = self.opacity_max_spin.value()
        self.settings["rotation_min"] = self.rotation_min_spin.value()
        self.settings["rotation_max"] = self.rotation_max_spin.value()
        self.accept()
    def get_settings(self):
        return self.settings

class StampManagerDialog(QtWidgets.QDialog):
    def __init__(self, registered_stamps: dict, global_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("스탬프 이미지 관리")
        self.setMinimumSize(450, 350)
        self.stamps = copy.deepcopy(registered_stamps)
        self.global_settings = global_settings
        layout = QtWidgets.QVBoxLayout(self)
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(self.stamps.keys())
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        button_layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("이미지 추가...")
        remove_button = QtWidgets.QPushButton("선택 삭제")
        import_button = QtWidgets.QPushButton("가져오기...")
        export_button = QtWidgets.QPushButton("내보내기...")
        self.settings_button = QtWidgets.QPushButton("선택한 스탬프 서식 수정...")
        add_button.clicked.connect(self.add_stamp)
        remove_button.clicked.connect(self.remove_stamp)
        import_button.clicked.connect(self.import_stamps)
        export_button.clicked.connect(self.export_stamps)
        self.settings_button.clicked.connect(self.edit_stamp_settings)
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addStretch(1)
        button_layout.addWidget(import_button)
        button_layout.addWidget(export_button)
        dialog_buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(QtWidgets.QLabel("등록된 스탬프 목록:"))
        layout.addWidget(self.list_widget)
        layout.addLayout(button_layout)
        layout.addWidget(self.settings_button)
        layout.addWidget(dialog_buttons)
        self.on_selection_changed()
    def on_selection_changed(self):
        has_selection = bool(self.list_widget.selectedItems())
        self.settings_button.setEnabled(has_selection)
    def edit_stamp_settings(self):
        current_item = self.list_widget.currentItem()
        if not current_item: return
        name = current_item.text()
        stamp_data = self.stamps[name]
        settings_to_edit = stamp_data.get("settings", self.global_settings)
        dialog = StampSettingsDialog(self)
        dialog.set_settings(settings_to_edit)
        if dialog.exec():
            stamp_data["settings"] = dialog.get_settings()
            QtWidgets.QMessageBox.information(self, "저장 완료", f"'{name}'의 개별 서식이 저장되었습니다.")
    def add_stamp(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "스탬프 이미지 선택", "", "PNG Files (*.png)")
        if not path: return
        default_name = os.path.splitext(os.path.basename(path))[0]
        while True:
            name, ok = QtWidgets.QInputDialog.getText(self, "스탬프 이름 입력", "이 스탬프의 이름을 입력하세요:", text=default_name)
            if not ok: return
            if name in self.stamps:
                QtWidgets.QMessageBox.warning(self, "이름 중복", f"'{name}' 이름은 이미 사용 중입니다. 다른 이름을 입력해주세요.")
                default_name = name
                continue
            break
        width_mm, ok = QtWidgets.QInputDialog.getDouble(self, "실제 크기 입력", "스탬프의 실제 가로 길이(mm)를 입력하세요:", 18.0, 1, 1000, 2)
        if not ok: return
        self.stamps[name] = {"path": path, "width_mm": width_mm}
        self.list_widget.addItem(name)
    def remove_stamp(self):
        current_item = self.list_widget.currentItem()
        if not current_item: return
        name = current_item.text()
        reply = QtWidgets.QMessageBox.question(self, "삭제 확인", f"'{name}' 스탬프를 목록에서 삭제하시겠습니까?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.list_widget.takeItem(self.list_widget.row(current_item))
            del self.stamps[name]
    def get_stamps(self):
        return self.stamps
    def import_stamps(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "스탬프 설정 가져오기", "", "Stamp Files (*.stamp)")
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                imported_stamps = json.load(f)
            if not isinstance(imported_stamps, dict):
                raise ValueError("올바른 스탬프 파일 형식이 아닙니다.")
            count = len(imported_stamps)
            reply = QtWidgets.QMessageBox.question(self, "가져오기 옵션", f"{count}개의 스탬프를 가져옵니다.\n기존에 이름이 같은 스탬프가 있으면 덮어쓸까요?", QtWidgets.QMessageBox.YesToAll | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.YesToAll)
            if reply == QtWidgets.QMessageBox.Cancel: return
            imported_count = 0
            for name, data in imported_stamps.items():
                if name in self.stamps and reply == QtWidgets.QMessageBox.No: continue
                self.stamps[name] = data
                imported_count += 1
            self.list_widget.clear()
            self.list_widget.addItems(self.stamps.keys())
            QtWidgets.QMessageBox.information(self, "성공", f"{imported_count}개의 스탬프를 성공적으로 가져왔습니다.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "가져오기 실패", f"파일을 읽는 중 오류가 발생했습니다:\n{e}")
    def export_stamps(self):
        if not self.stamps:
            QtWidgets.QMessageBox.warning(self, "알림", "내보낼 스탬프가 없습니다.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "스탬프 설정 내보내기", "my_stamps.stamp", "Stamp Files (*.stamp)")
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.stamps, f, ensure_ascii=False, indent=4)
            QtWidgets.QMessageBox.information(self, "성공", f"스탬프 설정을 성공적으로 내보냈습니다:\n{path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "내보내기 실패", f"파일을 저장하는 중 오류가 발생했습니다:\n{e}")

class ShortcutHelpDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("단축키 목록")
            self.setMinimumSize(600, 700)
            self.shortcut_data = []
            try:
                csv_path = resource_path("resources/data/shortcuts.csv")
                df = pd.read_csv(csv_path)
                self.shortcut_data = [tuple(row) for row in df.itertuples(index=False)]
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "파일 오류", f"단축키 목록 파일을 불러올 수 없습니다:\n{e}")
            layout = QtWidgets.QVBoxLayout(self)
            self.table = QtWidgets.QTableWidget()
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["기능 그룹", "기능 설명", "단축키"])
            self.table.setRowCount(len(self.shortcut_data))
            for row, (group, desc, shortcut) in enumerate(self.shortcut_data):
                item_group = QtWidgets.QTableWidgetItem(group)
                item_desc = QtWidgets.QTableWidgetItem(desc)
                item_shortcut = QtWidgets.QTableWidgetItem(shortcut)
                item_group.setTextAlignment(QtCore.Qt.AlignCenter)
                item_desc.setTextAlignment(QtCore.Qt.AlignCenter)
                item_shortcut.setTextAlignment(QtCore.Qt.AlignCenter)
                self.table.setItem(row, 0, item_group)
                self.table.setItem(row, 1, item_desc)
                self.table.setItem(row, 2, item_shortcut)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            pal = self.table.palette()
            pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(245, 245, 245))
            self.table.setPalette(pal)
            header = self.table.horizontalHeader()
            font_size = header.font().pointSize() + 2
            header.setStyleSheet(f"QHeaderView::section {{ background-color: black; color: white; font-weight: bold; font-size: {font_size}pt; padding: 4px; border: 0px; border-bottom: 2px double #555555; }}")
            self.table.resizeColumnsToContents()
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            self.export_button = QtWidgets.QPushButton("엑셀 파일로 저장...")
            self.export_button.clicked.connect(self.export_to_excel)
            button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
            button_box.rejected.connect(self.reject)
            button_layout = QtWidgets.QHBoxLayout()
            button_layout.addWidget(self.export_button)
            button_layout.addStretch(1)
            button_layout.addWidget(button_box)
            layout.addWidget(self.table)
            layout.addLayout(button_layout)
    def export_to_excel(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "엑셀 파일로 저장", "단축키_목록.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        try:
            df = pd.DataFrame(self.shortcut_data, columns=["기능 그룹", "기능 설명", "단축키"])
            df.to_excel(path, index=False)
            QtWidgets.QMessageBox.information(self, "저장 완료", f"엑셀 파일 저장 완료:\n{path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "저장 실패", f"엑셀 파일 저장 중 오류 발생:\n{e}")

class NumberingModeDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("넘버링 방식 선택")
        self.setMinimumWidth(550)
        self.choice = "global"
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 제목
        title_label = QtWidgets.QLabel("넘버링 방식 선택")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #09090B;")
        layout.addWidget(title_label)
        
        # 설명
        label = QtWidgets.QLabel("2페이지 이상 작업을 할 경우 모드 설정입니다.\n넘버링 방식을 선택해주세요.")
        label.setStyleSheet("font-size: 14px; color: #71717A; margin-bottom: 8px;")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        
        # 버튼들
        btn_global = QtWidgets.QPushButton("전체 페이지 이어서 넘버링\n(P.1: 1, 2 / P.2: 3, 4 ...)")
        btn_global.setMinimumHeight(60)
        btn_global.clicked.connect(self.select_global)
        layout.addWidget(btn_global)
        
        btn_page = QtWidgets.QPushButton("페이지마다 새로 넘버링\n(P.1: 1, 2 / P.2: 1, 2 ...)")
        btn_page.setProperty("buttonStyle", "secondary")
        btn_page.setMinimumHeight(60)
        btn_page.clicked.connect(self.select_page)
        layout.addWidget(btn_page)
    def select_global(self):
        self.choice = "global"
        self.accept()
    def select_page(self):
        self.choice = "page_specific"
        self.accept()
        


# ui/dialogs.py 파일 맨 아래에 추가
class SaveOptionsDialog(QtWidgets.QDialog):
    """3D 모델 저장 방식을 묻는 대화상자"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("저장 옵션 선택")
        self.setMinimumWidth(500)
        self.save_option = "link"

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 제목
        title_label = QtWidgets.QLabel("저장 옵션 선택")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #09090B;")
        layout.addWidget(title_label)
        
        # 설명
        label = QtWidgets.QLabel("3D 모델 파일의 저장 방식을 선택해주세요.")
        label.setStyleSheet("font-size: 14px; color: #71717A; margin-bottom: 8px;")
        layout.addWidget(label)

        # 옵션 그룹
        options_group = QtWidgets.QGroupBox()
        options_group.setStyleSheet("QGroupBox { border: none; padding: 0; margin: 0; }")
        options_layout = QtWidgets.QVBoxLayout(options_group)
        options_layout.setSpacing(12)
        
        self.radio_link = QtWidgets.QRadioButton("경로만 저장 (작은 파일 크기, 원본 파일 유지 필요)")
        self.radio_link.setChecked(True)
        self.radio_link.toggled.connect(lambda: self.set_option("link"))
        
        self.radio_embed = QtWidgets.QRadioButton("파일을 프로젝트에 포함하여 저장 (완전한 백업, 파일 크기 커짐)")
        self.radio_embed.toggled.connect(lambda: self.set_option("embed"))
        
        options_layout.addWidget(self.radio_link)
        options_layout.addWidget(self.radio_embed)
        layout.addWidget(options_group)
        
        layout.addStretch()
        
        # 버튼
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()
        
        cancel_button = QtWidgets.QPushButton("취소")
        cancel_button.setProperty("buttonStyle", "secondary")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        
        save_button = QtWidgets.QPushButton("저장")
        save_button.setMinimumWidth(100)
        save_button.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

    def set_option(self, option):
        self.save_option = option

    @staticmethod
    def get_save_option(parent=None):
        dialog = SaveOptionsDialog(parent)
        if dialog.exec():
            return dialog.save_option
        return None