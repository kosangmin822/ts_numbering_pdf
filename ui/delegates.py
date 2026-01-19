# ui/delegates.py

from PySide6 import QtWidgets, QtCore, QtGui
from typing import List

class ComboDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, options: List[str], parent=None):
        super().__init__(parent); self.options=options
    def createEditor(self, parent, opt, idx):
        cb=QtWidgets.QComboBox(parent); cb.addItems(self.options); return cb
    def setEditorData(self, ed, idx):
        t=idx.data(QtCore.Qt.EditRole) or idx.data(QtCore.Qt.DisplayRole) or ""
        ed.setCurrentIndex(max(0, ed.findText(t)))
    def setModelData(self, ed, model, idx): model.setData(idx, ed.currentText(), QtCore.Qt.EditRole)

class NumericDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        
        # 현재 행의 Type(컬럼 1)을 확인하여 기하공차 여부 판단
        type_idx = index.sibling(index.row(), 1)
        dim_type = type_idx.data(QtCore.Qt.DisplayRole) or ""
        
        # 선형 치수 목록 (음수 허용)
        linear_types = ["선형", "Ø", "R", "C", "기타"]
        
        # 기하공차 등은 음수 입력 방지
        # (단, dim_type이 아예 없거나 하는 경우엔 기본적으로 음수 허용하는게 안전할 수도 있으나,
        #  사용자 요청에 따라 GD&T로 추정되면 막음)
        if dim_type and dim_type not in linear_types:
            # 양수만 허용 (소수점 포함)
            regex = QtCore.QRegularExpression("[+]?\\d*\\.?\\d*")
        else:
            # 음수도 허용
            regex = QtCore.QRegularExpression("[+-]?\\d*\\.?\\d*")
            
        validator = QtGui.QRegularExpressionValidator(regex, editor)
        editor.setValidator(validator)
        return editor