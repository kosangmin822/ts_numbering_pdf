# -*- coding: utf-8 -*-
"""
UIManager - UI 관리 전담 클래스
메뉴, 툴바, 도크 위젯, 단축키 등 UI 관련 기능을 담당합니다.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from PySide6 import QtCore, QtGui, QtWidgets


class UIManager:
    """UI 관리 전담 클래스"""

    def __init__(self, main_window):
        """
        UIManager 초기화

        Args:
            main_window: 메인 윈도우 인스턴스 (의존성 주입)
        """
        self.main_window = main_window
        self.shortcuts = []

    def create_menus(self):
        """메뉴바를 생성합니다."""
        menubar = self.main_window.menuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu("파일")

        # 파일 메뉴 액션들 생성
        a_open = file_menu.addAction("Open Project…")
        a_open.triggered.connect(self.main_window.open_project_dialog)

        a_save = file_menu.addAction("Save Project")
        a_save.triggered.connect(self.main_window.save_project)

        a_save_as = file_menu.addAction("Save Project As…")
        a_save_as.triggered.connect(self.main_window.save_project_as)

        file_menu.addSeparator()

        a_open_3d = file_menu.addAction("import 3D Model...")
        a_open_3d.triggered.connect(self.main_window.open_3d_model)

        file_menu.addSeparator()

        a_publish = file_menu.addAction("서버에 발행 (테스트)...")
        a_publish.triggered.connect(self.main_window.publish_project)

        file_menu.addSeparator()

        a_imp = file_menu.addAction("Import PDF…")
        a_imp.triggered.connect(self.main_window.import_pdf)

        file_menu.addSeparator()

        a_pdf = file_menu.addAction("Export PDF…")
        a_pdf.triggered.connect(self.main_window._cmd_export_pdf)

        a_csv = file_menu.addAction("Export CSV…")
        a_csv.triggered.connect(self.main_window.export_csv_dialog)

        a_xlsx = file_menu.addAction("Export XLSX…")
        a_xlsx.triggered.connect(self.main_window.export_xlsx_dialog)

        # 보기 메뉴
        view_menu = menubar.addMenu("보기")

        a_num_settings = view_menu.addAction("넘버링 설정…")
        a_num_settings.triggered.connect(self.main_window.open_numbering_settings)

        view_menu.addSeparator()

        # 하이라이트 액션 생성
        self.main_window.a_highlight = view_menu.addAction("항목 하이라이트 켜기")
        self.main_window.a_highlight.setCheckable(True)
        self.main_window.a_highlight.setChecked(True)
        self.main_window.a_highlight.toggled.connect(self.main_window.toggle_highlighting)
        self.main_window.a_highlight.setShortcut("Ctrl+H")

        # 흐름도 보기 액션 생성
        self.main_window.a_flow_menu = view_menu.addAction("흐름도 보기")
        self.main_window.a_flow_menu.setCheckable(True)
        self.main_window.a_flow_menu.setChecked(self.main_window.flow_view_enabled)
        self.main_window.a_flow_menu.triggered.connect(self.main_window.toggle_flow_view)

        view_menu.addSeparator()

        a_fit = view_menu.addAction("화면 맞춤")
        a_fit.triggered.connect(self.main_window.fit_to_window)

        self.main_window.a_auto_hi = view_menu.addAction("고해상도 자동 재렌더")
        self.main_window.a_auto_hi.setCheckable(True)
        self.main_window.a_auto_hi.setChecked(True)
        self.main_window.a_auto_hi.toggled.connect(self.main_window.set_auto_highres)

        a_rerender = view_menu.addAction("현재 배율로 재렌더")
        a_rerender.triggered.connect(self.main_window.rerender_now)

        view_menu.addSeparator()

        a_shortcuts = view_menu.addAction("단축키 보기...")
        a_shortcuts.triggered.connect(self.main_window.show_shortcut_help)

        # 모드선택 메뉴
        mode_menu = menubar.addMenu("모드선택")

        self.main_window.a_only = mode_menu.addAction("Numbering Only")
        self.main_window.a_only.setCheckable(True)
        self.main_window.a_inp = mode_menu.addAction("Numbering + Input Demension")
        self.main_window.a_inp.setCheckable(True)

        mode_group = QtGui.QActionGroup(self.main_window)
        mode_group.setExclusive(True)
        mode_group.addAction(self.main_window.a_only)
        mode_group.addAction(self.main_window.a_inp)
        self.main_window.a_only.setChecked(True)
        self.main_window.a_only.triggered.connect(lambda: self.main_window.set_input_mode("number_only"))
        self.main_window.a_inp.triggered.connect(lambda: self.main_window.set_input_mode("with_input"))

        # 옵션 메뉴
        options_menu = menubar.addMenu("옵션")

        a_start = options_menu.addAction("Set Start Number…")
        a_start.triggered.connect(self.main_window.set_start_number)

        options_menu.addSeparator()

        a_manage_stamps_menu = options_menu.addAction("스탬프 이미지 관리…")
        a_manage_stamps_menu.triggered.connect(self.main_window.open_stamp_manager)

        # Windows 메뉴
        windows_menu = menubar.addMenu("Windows")

        self.main_window.a_pdf_preview = windows_menu.addAction("1. PDF Page Preview")
        self.main_window.a_pdf_preview.setCheckable(True)
        self.main_window.a_pdf_preview.setChecked(True)
        self.main_window.a_pdf_preview.triggered.connect(self.main_window.toggle_pdf_preview)

        self.main_window.a_3d_navigator = windows_menu.addAction("2. 3D Viewport Navigator")
        self.main_window.a_3d_navigator.setCheckable(True)
        self.main_window.a_3d_navigator.setChecked(True)
        self.main_window.a_3d_navigator.triggered.connect(self.main_window.toggle_3d_navigator)

        self.main_window.a_2d_viewer = windows_menu.addAction("3. 2D Viewer")
        self.main_window.a_2d_viewer.setCheckable(True)
        self.main_window.a_2d_viewer.triggered.connect(lambda: print("2D Viewer 토글"))

        self.main_window.a_3d_viewer = windows_menu.addAction("4. 3D Viewer")
        self.main_window.a_3d_viewer.setCheckable(True)
        self.main_window.a_3d_viewer.triggered.connect(lambda: print("3D Viewer 토글"))

        self.main_window.a_numbering_list = windows_menu.addAction("5. Numbering List")
        self.main_window.a_numbering_list.setCheckable(True)
        self.main_window.a_numbering_list.setChecked(True)
        self.main_window.a_numbering_list.triggered.connect(self.main_window.toggle_numbering_list)

        self.main_window.a_stamping_list = windows_menu.addAction("6. Stamping List")
        self.main_window.a_stamping_list.setCheckable(True)
        self.main_window.a_stamping_list.triggered.connect(lambda: print("Stamping List 토글"))

        self.main_window.a_flowchart_viewer = windows_menu.addAction("7. Flowchart Viewer")
        self.main_window.a_flowchart_viewer.setCheckable(True)
        self.main_window.a_flowchart_viewer.triggered.connect(lambda: print("Flowchart Viewer 토글"))

        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")

        a_help = help_menu.addAction("도움말")
        a_help.triggered.connect(lambda: print("도움말 기능은 준비 중입니다."))

        a_about = help_menu.addAction("정보")
        a_about.triggered.connect(self.main_window.show_about_dialog)

    def create_toolbar(self):
        """툴바를 생성합니다."""
        # 원래 툴바 생성 로직을 그대로 유지
        # 이 함수는 main.py의 원래 _create_toolbar 함수를 호출하도록 수정
        pass

    def _create_toolbar_group(self, actions: List[QtGui.QAction], text_label: str) -> QtWidgets.QWidget:
        """
        툴바 그룹을 생성합니다.

        Args:
            actions: 액션 리스트
            text_label: 그룹 라벨
        Returns:
            QWidget: 그룹 위젯
        """
        group_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(group_widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        # 그룹 라벨
        label = QtWidgets.QLabel(text_label)
        label.setStyleSheet("font-weight: bold; color: #666;")
        layout.addWidget(label)

        # 구분선
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.VLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(separator)

        # 액션 버튼들
        for action in actions:
            button = QtWidgets.QToolButton()
            button.setDefaultAction(action)
            button.setToolButtonStyle(QtWidgets.QToolButton.ToolButtonIconOnly)
            layout.addWidget(button)

        layout.addStretch()
        return group_widget

    def create_shortcuts(self):
        """단축키를 생성합니다."""
        from PySide6 import QtGui

        QtGui.QShortcut(
            QtGui.QKeySequence.Delete, self.main_window.stamp_table, activated=self.main_window._delete_selected_stamps
        )

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+N"), self.main_window, activated=self.main_window.new_project)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self.main_window, activated=self.main_window.open_project_dialog)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self.main_window, activated=self.main_window.save_project)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+S"), self.main_window, activated=self.main_window.save_project_as)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+I"), self.main_window, activated=self.main_window.import_pdf)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self.main_window, activated=self.main_window.undo)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Y"), self.main_window, activated=self.main_window.redo)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+E"), self.main_window, activated=self.main_window._cycle_active_mode)

        QtGui.QShortcut(QtGui.QKeySequence("Insert"), self.main_window.table, activated=self.main_window.insert_excel_style)

        QtGui.QShortcut(
            QtGui.QKeySequence("Shift+Insert"), self.main_window.table, activated=self.main_window.insert_precision_style
        )

        QtGui.QShortcut(QtGui.QKeySequence("Delete"), self.main_window.table, activated=self.main_window.delete_items)

        QtGui.QShortcut(
            QtGui.QKeySequence("Shift+Delete"), self.main_window.table, activated=self.main_window.renumber_items_by_unit
        )

        QtGui.QShortcut(QtGui.QKeySequence("F2"), self.main_window.table, activated=self.main_window.set_individual_style)

        esc_shortcut = QtGui.QShortcut(QtGui.QKeySequence.Cancel, self.main_window)
        esc_shortcut.activated.connect(self.main_window.cancel_insert_mode)
        esc_shortcut.activated.connect(self.main_window.clear_selection_and_highlight)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self.main_window, activated=self.main_window.fit_to_window)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), self.main_window, activated=self.main_window.rerender_now)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+F"), self.main_window, activated=self.main_window.toggle_flow_view)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+P"), self.main_window, activated=self.main_window.toggle_preview_mode)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl++"), self.main_window, activated=self.main_window.view.zoom_in)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+-"), self.main_window, activated=self.main_window.view.zoom_out)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self.main_window, activated=self.main_window.view.reset_zoom)

        QtGui.QShortcut(QtGui.QKeySequence("F1"), self.main_window, activated=self.main_window.show_shortcut_help)



        QtGui.QShortcut(QtGui.QKeySequence.MoveToPreviousPage, self.main_window, activated=self.main_window.go_prev)

        QtGui.QShortcut(QtGui.QKeySequence.MoveToNextPage, self.main_window, activated=self.main_window.go_next)

        egg_sc = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F12"), self.main_window)
        egg_sc.activated.connect(self.main_window._on_egg_hotkey)
        egg_sc.setAutoRepeat(False)
        QtGui.QShortcut(
            QtGui.QKeySequence("Ctrl+F11"), self.main_window, activated=lambda: self.main_window.toggle_shooting_mode(False)
        )
        QtGui.QShortcut(
            QtGui.QKeySequence("F5"), self.main_window, activated=lambda: self.main_window.set_input_mode("number_only")
        )
        # F6: 뷰 정렬 (가장 큰 축만 남기고 나머지는 0으로 정렬)
        QtGui.QShortcut(QtGui.QKeySequence("F6"), self.main_window, activated=self.main_window.align_view_axis)
        QtGui.QShortcut(
            QtGui.QKeySequence("Shift+F1"),
            self.main_window,
            activated=lambda: self.main_window.adjust_label_style("radius_view_px", 2),
        )
        QtGui.QShortcut(
            QtGui.QKeySequence("Shift+F2"),
            self.main_window,
            activated=lambda: self.main_window.adjust_label_style("radius_view_px", -2),
        )
        QtGui.QShortcut(
            QtGui.QKeySequence("Shift+F3"),
            self.main_window,
            activated=lambda: self.main_window.adjust_label_style("stroke_width", 1),
        )
        QtGui.QShortcut(
            QtGui.QKeySequence("Shift+F4"),
            self.main_window,
            activated=lambda: self.main_window.adjust_label_style("stroke_width", -1),
        )
        QtGui.QShortcut(
            QtGui.QKeySequence("Shift+F5"),
            self.main_window,
            activated=lambda: self.main_window.adjust_label_style("font_size_view_px", 2),
        )
        QtGui.QShortcut(
            QtGui.QKeySequence("Shift+F6"),
            self.main_window,
            activated=lambda: self.main_window.adjust_label_style("font_size_view_px", -2),
        )



    def setup_3d_viewer_color_controls(self):
        """3D 뷰어 색상 컨트롤을 설정합니다."""
        if not hasattr(self.main_window, 'plotter') or self.main_window.plotter is None:
            return

        # 색상 팔레트 생성
        color_palette = self._create_color_palette()

        # 3D 뷰어에 색상 컨트롤 추가
        if hasattr(self.main_window, 'vlayout_3d'):
            self.main_window.vlayout_3d.addWidget(color_palette)

    def _create_color_palette(self) -> QtWidgets.QWidget:
        """색상 팔레트를 생성합니다."""
        palette_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(palette_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 색상 버튼들
        colors = [
            ("흰색", QtCore.Qt.white),
            ("검정", QtCore.Qt.black),
            ("빨강", QtCore.Qt.red),
            ("초록", QtCore.Qt.green),
            ("파랑", QtCore.Qt.blue),
            ("노랑", QtCore.Qt.yellow),
            ("자홍", QtCore.Qt.magenta),
            ("청록", QtCore.Qt.cyan),
        ]

        for name, color in colors:
            button = QtWidgets.QPushButton(name)
            button.setFixedSize(60, 30)
            button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #ccc;")
            button.clicked.connect(lambda checked, c=color: self._on_color_selected(c))
            layout.addWidget(button)

        # 투명도 슬라이더
        layout.addWidget(QtWidgets.QLabel("투명도:"))
        transparency_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        transparency_slider.setRange(0, 100)
        transparency_slider.setValue(0)
        transparency_slider.valueChanged.connect(self.main_window.change_transparency)
        layout.addWidget(transparency_slider)

        # 리셋 버튼
        reset_button = QtWidgets.QPushButton("리셋")
        reset_button.clicked.connect(self.main_window.reset_3d_colors)
        layout.addWidget(reset_button)

        layout.addStretch()
        return palette_widget

    def _on_color_selected(self, color: QtGui.QColor):
        """색상이 선택되었을 때 처리합니다."""
        if hasattr(self.main_window, 'change_background_color'):
            # 배경색 변경 로직
            if hasattr(self.main_window, 'plotter') and self.main_window.plotter:
                try:
                    r = color.red() / 255.0
                    g = color.green() / 255.0
                    b = color.blue() / 255.0
                    self.main_window.plotter.background_color = (r, g, b)
                    self.main_window.plotter.render()
                except Exception as e:
                    print(f"색상 변경 오류: {e}")

    def create_preview_items(self):
        """미리보기 아이템들을 생성합니다."""
        if not hasattr(self.main_window, 'preview_scene'):
            return

        # 미리보기 아이템 생성 로직
        # 구체적인 구현은 main.py의 _create_preview_items 함수를 참조
        pass

    def setup_dock_widgets(self):
        """도크 위젯들을 설정합니다."""
        # 페이지 도크
        if hasattr(self.main_window, 'page_dock'):
            self.main_window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.main_window.page_dock)

        # 3D Navigator 도크
        if hasattr(self.main_window, 'navigator_dock'):
            self.main_window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.main_window.navigator_dock)

        # 넘버링 리스트 도크
        if hasattr(self.main_window, 'dock'):
            self.main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.main_window.dock)

    def update_ui_state(self):
        """UI 상태를 업데이트합니다."""
        # 현재 모드에 따른 UI 상태 업데이트
        if hasattr(self.main_window, 'active_mode'):
            mode = self.main_window.active_mode

            # 모드별 UI 활성화/비활성화
            if mode == "view":
                self._set_view_mode_ui()
            elif mode == "numbering":
                self._set_numbering_mode_ui()
            elif mode == "stamp":
                self._set_stamp_mode_ui()

    def _set_view_mode_ui(self):
        """뷰 모드 UI를 설정합니다."""
        # 뷰 모드 관련 UI 설정
        pass

    def _set_numbering_mode_ui(self):
        """넘버링 모드 UI를 설정합니다."""
        # 넘버링 모드 관련 UI 설정
        pass

    def _set_stamp_mode_ui(self):
        """스탬프 모드 UI를 설정합니다."""
        # 스탬프 모드 관련 UI 설정
        pass

    def cleanup_shortcuts(self):
        """단축키를 정리합니다."""
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
        self.shortcuts.clear()

    def create_toolbar_group(self, actions, text_label):
        """버튼(Action) 리스트와 제목을 받아 하나의 그룹 상자 위젯을 생성합니다."""
        group_box = QtWidgets.QGroupBox(text_label)
        group_box.setAlignment(QtCore.Qt.AlignCenter)
        group_layout = QtWidgets.QVBoxLayout(group_box)
        # 위쪽 여백을 12로 늘려 아이콘과 제목 사이의 공간 확보
        group_layout.setContentsMargins(0, 12, 0, 2)
        group_layout.setSpacing(0)
        # 버튼들을 담을 툴바 생성
        button_toolbar = QtWidgets.QToolBar()
        button_toolbar.setIconSize(QtCore.QSize(36, 36))
        for action in actions:
            if action is None:  # None 이면 서브 구분선 추가
                sub_separator = self.main_window._create_sub_separator()
                button_toolbar.addWidget(sub_separator)
            else:
                button_toolbar.addAction(action)
        # 그룹 레이아웃에 툴바 추가
        group_layout.addWidget(button_toolbar)
        return group_box

    def add_toolbar_action(
        self, toolbar, icon_path_qrc: str, text: str, slot, checkable=False, checked=False
    ):
        """툴바에 액션을 추가합니다."""
        act = QtGui.QAction(QtGui.QIcon(icon_path_qrc), text, self.main_window)
        act.setCheckable(checkable)
        if checkable:
            act.setChecked(checked)
        act.triggered.connect(slot)
        toolbar.addAction(act)
        return act
