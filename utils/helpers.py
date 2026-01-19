# utils/helpers.py

import os
import sys
import traceback
from PySide6 import QtWidgets, QtGui

def _apply_page_rotation_xy(x: float, y: float, w: float, h: float, rot: int) -> tuple[float, float]:
    r = rot % 360
    if r == 0: return x, y
    elif r == 90: return y, w - x
    elif r == 180: return w - x, h - y
    elif r == 270: return h - y, x
    return x, y

def _log_error(self, title: str, exc: Exception):
    msg = f"{title}\n{exc}\n\n{traceback.format_exc()}"
    try:
        with open("tsn_error.log", "a", encoding="utf-8") as f:
            f.write(msg + "\n" + ("-"*60) + "\n")
    except:
        pass
    QtWidgets.QMessageBox.critical(self, title, str(exc))

def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

def dim_prefix(t: str) -> str:
    if t in ("선형", "기타"): return ""
    # "⏤(진직도)" 형식에서 "⏤" 추출
    if "(" in t:
        return t.split("(")[0]
    # 하위 호환성: 공백이 있으면 첫 번째 단어(기호)만 반환
    if " " in t:
        return t.split(" ")[0]
    return t
def dim_format(t: str, v: str) -> str: return f"{dim_prefix(t)}{v}".strip()
def strip_prefix_for_value(t: str, s: str) -> str:
    pre = dim_prefix(t); s = (s or "").strip()
    return s[len(pre):].strip() if pre and s.startswith(pre) else s

def to_float_or_none(s):
    try:
        if s is None: return None
        s=str(s).strip().replace(",","")
        if s=="": return None
        return float(s)
    except: return None

def fmt_signed2(v: float|None) -> str: return "" if v is None else f"{v:+.2f}"
def normalize_signed_text(s: str) -> str:
    v=to_float_or_none(s)
    return fmt_signed2(v) if v is not None else ("" if s is None or str(s).strip()=="" else str(s).strip())

def qrgba(c: QtGui.QColor): return (c.red(),c.green(),c.blue(),c.alpha())
def from_rgba(rgba): r,g,b,a=rgba; c=QtGui.QColor(r,g,b); c.setAlpha(a); return c
def icon_if(filename: str) -> QtGui.QIcon:
    try:
        return QtGui.QIcon(resource_path(filename))
    except Exception:
        return QtGui.QIcon()