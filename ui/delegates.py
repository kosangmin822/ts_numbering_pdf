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
        regex = QtCore.QRegularExpression("[+-]?\\d*\\.?\\d*")
        validator = QtGui.QRegularExpressionValidator(regex, editor)
        editor.setValidator(validator)
        return editor