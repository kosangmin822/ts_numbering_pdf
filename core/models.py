# core/models.py

from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from PySide6 import QtGui

# 이 파일이 utils 폴더 안의 helpers.py 파일에 있는 함수를 사용하게 됩니다.
# 아직 helpers.py를 만들지 않았지만, 미리 import 구문을 넣어둡니다.
from utils.helpers import qrgba, from_rgba

@dataclass
class MarkItem:
    no: float
    page_index: int
    pdf_point: Tuple[float,float]
    dim_type: str="선형"
    value: str=""
    tol_plus: str=""
    tol_minus: str=""
    custom_style: Optional[LabelStyle] = None
    viewport_parameters: str = ""  # 3D ??? ???? JSON ???
    x_values: List[str] = field(default_factory=lambda: ["", "", "", "", ""])

@dataclass
class StampItem:
    stamp_key: str
    page_index: int
    pdf_point: Tuple[float, float]
    opacity: float = 1.0
    rotation: float = 0.0
    scale: float = 1.0
    color_tint: Optional[Tuple[int, int, int, int]] = None

class LabelStyle:
    def __init__(self):
        self.radius_view_px=12
        self.stroke_width=2
        self.font_size_view_px=12
        self.fill_color=QtGui.QColor(255,255,255,0)
        self.stroke_color=QtGui.QColor("red")
        self.text_color=QtGui.QColor("black")
        self.fill_none=True
        self.flow_line_opacity = 0.5
        self.flow_line_color = QtGui.QColor("#555555")
        self.flow_line_style = "solid"
        self.flow_show_start_end = False
        self.flow_arrow_style = "arrow"
        self.shape = "circle"  # circle, rectangle, triangle, star, none

    def to_dict(self):
        return {"radius_view_px":self.radius_view_px,"stroke_width":self.stroke_width,
                "font_size_view_px":self.font_size_view_px,
                "fill_color":qrgba(self.fill_color),"stroke_color":qrgba(self.stroke_color),
                "text_color":qrgba(self.text_color),"fill_none":self.fill_none,
                "flow_line_opacity":self.flow_line_opacity,
                "flow_line_color": qrgba(self.flow_line_color),
                "flow_line_style": self.flow_line_style,
                "flow_show_start_end": self.flow_show_start_end,
                "flow_arrow_style": self.flow_arrow_style,
                "shape": self.shape,
                }

    def from_dict(self,d):
        self.radius_view_px=int(d.get("radius_view_px",self.radius_view_px))
        self.stroke_width=int(d.get("stroke_width",self.stroke_width))
        self.font_size_view_px=int(d.get("font_size_view_px",self.font_size_view_px))
        self.fill_color=from_rgba(tuple(d.get("fill_color",qrgba(self.fill_color))))
        self.stroke_color=from_rgba(tuple(d.get("stroke_color",qrgba(self.stroke_color))))
        self.text_color=from_rgba(tuple(d.get("text_color",qrgba(self.text_color))))
        self.fill_none=bool(d.get("fill_none",self.fill_none))
        self.flow_line_opacity = float(d.get("flow_line_opacity", 0.5))
        self.flow_line_color = from_rgba(tuple(d.get("flow_line_color", qrgba(self.flow_line_color))))
        self.flow_line_style = str(d.get("flow_line_style", self.flow_line_style))
        self.flow_show_start_end = bool(d.get("flow_show_start_end", self.flow_show_start_end))
        self.flow_arrow_style = str(d.get("flow_arrow_style", self.flow_arrow_style))
        self.shape = str(d.get("shape", self.shape))
