# ui/styles.py
"""
shadcn 스타일을 적용한 전역 스타일시트
"""

# shadcn 스타일 색상 팔레트
COLORS = {
    # Primary Colors
    "background": "#FFFFFF",
    "foreground": "#09090B",
    "card": "#FFFFFF",
    "card_foreground": "#09090B",
    "popover": "#FFFFFF",
    "popover_foreground": "#09090B",
    
    # Muted Colors
    "muted": "#F4F4F5",
    "muted_foreground": "#71717A",
    
    # Accent Colors
    "accent": "#F4F4F5",
    "accent_foreground": "#18181B",
    
    # Primary/Brand Color
    "primary": "#18181B",
    "primary_foreground": "#FAFAFA",
    
    # Secondary Color
    "secondary": "#F4F4F5",
    "secondary_foreground": "#18181B",
    
    # Destructive/Error
    "destructive": "#EF4444",
    "destructive_foreground": "#FAFAFA",
    
    # Border & Input
    "border": "#E4E4E7",
    "input": "#E4E4E7",
    "ring": "#18181B",
    
    # Success & Info
    "success": "#10B981",
    "info": "#3B82F6",
    "warning": "#F59E0B",
}

# 그림자 스타일
SHADOWS = {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
}

# 전역 스타일시트
GLOBAL_STYLESHEET = f"""
/* 전역 설정 - 시스템 색상 의존성 제거 */
* {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: {COLORS['foreground']};
    background-color: {COLORS['background']};
    selection-background-color: {COLORS['primary']};
    selection-color: {COLORS['primary_foreground']};
}}

QMainWindow {{
    background-color: {COLORS['background']};
    color: {COLORS['foreground']};
}}

/* 마우스 커서는 프로그램 코드에서 직접 설정 */

/* 버튼 스타일 */
QPushButton {{
    background-color: {COLORS['primary']};
    color: {COLORS['primary_foreground']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 500;
    min-height: 36px;
}}

QPushButton:hover {{
    background-color: #27272A;
    border-color: #3F3F46;
}}

QPushButton:pressed {{
    background-color: #3F3F46;
}}

QPushButton:disabled {{
    background-color: {COLORS['muted']};
    color: {COLORS['muted_foreground']};
    border-color: {COLORS['border']};
}}

/* Secondary 버튼 */
QPushButton[buttonStyle="secondary"] {{
    background-color: {COLORS['secondary']};
    color: {COLORS['secondary_foreground']};
    border: 1px solid {COLORS['border']};
}}

QPushButton[buttonStyle="secondary"]:hover {{
    background-color: #E4E4E7;
}}

/* Destructive 버튼 */
QPushButton[buttonStyle="destructive"] {{
    background-color: {COLORS['destructive']};
    color: {COLORS['destructive_foreground']};
    border: 1px solid {COLORS['destructive']};
}}

QPushButton[buttonStyle="destructive"]:hover {{
    background-color: #DC2626;
}}

/* 입력 필드 */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['background']};
    border: 1px solid {COLORS['input']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    color: {COLORS['foreground']};
    selection-background-color: {COLORS['primary']};
    selection-color: {COLORS['primary_foreground']};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {COLORS['ring']};
    padding: 7px 11px;
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {COLORS['muted']};
    color: {COLORS['muted_foreground']};
}}

/* 콤보박스 */
QComboBox {{
    background-color: {COLORS['background']};
    border: 1px solid {COLORS['input']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    min-height: 36px;
}}

QComboBox:hover {{
    border-color: {COLORS['ring']};
}}

QComboBox:focus {{
    border: 2px solid {COLORS['ring']};
    padding: 7px 11px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: url(none);
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {COLORS['foreground']};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['popover']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {COLORS['accent']};
    selection-color: {COLORS['accent_foreground']};
    outline: none;
}}

/* 스핀박스 */
QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['background']};
    border: 1px solid {COLORS['input']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    min-height: 36px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {COLORS['ring']};
    padding: 7px 11px;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: transparent;
    border: none;
    width: 20px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {COLORS['muted']};
}}

/* 슬라이더 */
QSlider::groove:horizontal {{
    background: {COLORS['secondary']};
    height: 4px;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {COLORS['primary']};
    border: 2px solid {COLORS['background']};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: #27272A;
}}

/* 체크박스 */
QCheckBox {{
    spacing: 8px;
    font-size: 14px;
    color: {COLORS['foreground']};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {COLORS['input']};
    border-radius: 4px;
    background-color: {COLORS['background']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['ring']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
    image: url(none);
}}

/* 라디오 버튼 */
QRadioButton {{
    spacing: 8px;
    font-size: 14px;
    color: {COLORS['foreground']};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {COLORS['input']};
    border-radius: 8px;
    background-color: {COLORS['background']};
}}

QRadioButton::indicator:hover {{
    border-color: {COLORS['ring']};
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}

/* 테이블 */
QTableWidget, QTableView {{
    background-color: {COLORS['background']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    gridline-color: {COLORS['border']};
    font-size: 14px;
    selection-background-color: {COLORS['accent']};
    selection-color: {COLORS['accent_foreground']};
}}

QTableWidget::item, QTableView::item {{
    padding: 8px;
    border-bottom: 1px solid {COLORS['border']};
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {COLORS['accent']};
    color: {COLORS['accent_foreground']};
}}

QHeaderView::section {{
    background-color: {COLORS['muted']};
    color: {COLORS['foreground']};
    font-weight: 600;
    font-size: 14px;
    padding: 12px 8px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    border-right: 1px solid {COLORS['border']};
}}

QHeaderView::section:first {{
    border-top-left-radius: 8px;
}}

QHeaderView::section:last {{
    border-top-right-radius: 8px;
    border-right: none;
}}

/* 리스트 위젯 */
QListWidget {{
    background-color: {COLORS['background']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
    font-size: 14px;
}}

QListWidget::item {{
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 0;
}}

QListWidget::item:hover {{
    background-color: {COLORS['accent']};
}}

QListWidget::item:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['primary_foreground']};
}}

/* 그룹박스 */
QGroupBox {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px;
    font-size: 14px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {COLORS['foreground']};
    background-color: {COLORS['background']};
    border-radius: 4px;
}}

/* 탭 위젯 */
QTabWidget::pane {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
}}

QTabBar::tab {{
    background-color: {COLORS['muted']};
    color: {COLORS['muted_foreground']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
    font-size: 14px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['card']};
    color: {COLORS['foreground']};
}}

QTabBar::tab:hover {{
    background-color: {COLORS['accent']};
}}

/* 스크롤바 */
QScrollBar:vertical {{
    background: {COLORS['muted']};
    width: 10px;
    border-radius: 5px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['muted_foreground']};
}}

QScrollBar:horizontal {{
    background: {COLORS['muted']};
    height: 10px;
    border-radius: 5px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS['border']};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS['muted_foreground']};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    border: none;
    background: none;
    height: 0px;
    width: 0px;
}}

/* 다이얼로그 */
QDialog {{
    background-color: {COLORS['background']};
}}

/* 메뉴 */
QMenuBar {{
    background-color: {COLORS['background']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 4px 0;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 14px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['accent']};
}}

QMenu {{
    background-color: {COLORS['popover']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 32px 8px 12px;
    border-radius: 4px;
    font-size: 14px;
}}

QMenu::item:selected {{
    background-color: {COLORS['accent']};
    color: {COLORS['accent_foreground']};
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 4px 8px;
}}

/* 툴바 */
QToolBar {{
    background-color: {COLORS['background']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    spacing: 8px;
    padding: 8px;
}}

QToolBar::separator {{
    background-color: {COLORS['border']};
    width: 1px;
    margin: 4px 8px;
}}

QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 8px;
    margin: 2px;
}}

QToolButton:hover {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['border']};
}}

QToolButton:pressed {{
    background-color: {COLORS['muted']};
}}

QToolButton:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['border']};
}}

/* 상태바 */
QStatusBar {{
    background-color: {COLORS['muted']};
    border-top: 1px solid {COLORS['border']};
    font-size: 12px;
    padding: 4px 8px;
}}

/* 툴팁 */
QToolTip {{
    background-color: {COLORS['popover']};
    color: {COLORS['popover_foreground']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* 프로그레스바 */
QProgressBar {{
    background-color: {COLORS['secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    text-align: center;
    font-size: 12px;
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 5px;
}}

/* 메시지박스 */
QMessageBox {{
    background-color: {COLORS['background']};
}}

QMessageBox QLabel {{
    font-size: 14px;
    color: {COLORS['foreground']};
}}

/* 다이얼로그 버튼 박스 */
QDialogButtonBox {{
    button-layout: 0;
}}
"""

# 다크 모드 색상 팔레트 (향후 확장용)
DARK_COLORS = {
    "background": "#09090B",
    "foreground": "#FAFAFA",
    "card": "#09090B",
    "card_foreground": "#FAFAFA",
    "popover": "#09090B",
    "popover_foreground": "#FAFAFA",
    "muted": "#27272A",
    "muted_foreground": "#A1A1AA",
    "accent": "#27272A",
    "accent_foreground": "#FAFAFA",
    "primary": "#FAFAFA",
    "primary_foreground": "#18181B",
    "secondary": "#27272A",
    "secondary_foreground": "#FAFAFA",
    "destructive": "#7F1D1D",
    "destructive_foreground": "#FAFAFA",
    "border": "#27272A",
    "input": "#27272A",
    "ring": "#D4D4D8",
    "success": "#10B981",
    "info": "#3B82F6",
    "warning": "#F59E0B",
}

