# ui/views.py

from PySide6 import QtWidgets, QtCore, QtGui

class PdfScene(QtWidgets.QGraphicsScene):
    clicked=QtCore.Signal(QtCore.QPointF); moved=QtCore.Signal(QtCore.QPointF)
    def mousePressEvent(self,e):
        if e.button()==QtCore.Qt.LeftButton: self.clicked.emit(e.scenePos())
        super().mousePressEvent(e)
    def mouseMoveEvent(self,e): self.moved.emit(e.scenePos()); super().mouseMoveEvent(e)

class PdfView(QtWidgets.QGraphicsView):
    zoom_changed=QtCore.Signal(float)
    def __init__(self, scene, parent=None):
        super().__init__(scene,parent)
        self.setRenderHints(QtGui.QPainter.Antialiasing|QtGui.QPainter.SmoothPixmapTransform)
        self.setMouseTracking(True)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self._panning=False; self._pan_start=QtCore.QPoint()
        self._min_scale=0.2; self._max_scale=8.0
    def _scale(self): return self.transform().m11()
    def _apply_scale(self, ns):
        ns=max(self._min_scale,min(self._max_scale,ns))
        cur=self._scale() or 1.0; factor=ns/cur
        if abs(factor-1.0)>1e-6: self.scale(factor,factor)
        self.zoom_changed.emit(self._scale())
    def wheelEvent(self,e):
        if e.modifiers() & QtCore.Qt.ControlModifier:
            self._apply_scale(self._scale()*(1.25 if e.angleDelta().y()>0 else 1/1.25)); e.accept(); return
        super().wheelEvent(e)
    def mousePressEvent(self,e):
        if e.button()==QtCore.Qt.MiddleButton:
            self._panning=True; self._pan_start=e.position().toPoint()
            self.setCursor(QtCore.Qt.ClosedHandCursor); e.accept(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        if self._panning:
            cur=e.position().toPoint(); delta=cur-self._pan_start; self._pan_start=cur
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-delta.y()); e.accept(); return
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(self,e):
        if e.button()==QtCore.Qt.MiddleButton and self._panning:
            self._panning=False; self.setCursor(QtCore.Qt.ArrowCursor); e.accept(); return
        super().mouseReleaseEvent(e)
    def zoom_in(self): self._apply_scale(self._scale()*1.2)
    def zoom_out(self): self._apply_scale(self._scale()/1.2)
    def reset_zoom(self): self._apply_scale(1.0)

class ThumbnailLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal(int)
    def __init__(self, page_index: int, pixmap: QtGui.QPixmap, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.setPixmap(pixmap)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setScaledContents(True)
        target_long_edge = 140.0
        pix_w = pixmap.width()
        pix_h = pixmap.height()
        if pix_w > pix_h:
            scale_ratio = target_long_edge / pix_w
            new_w = int(target_long_edge)
            new_h = int(pix_h * scale_ratio)
            self.setFixedSize(new_w, new_h)
        else:
            scale_ratio = target_long_edge / pix_h
            new_h = int(target_long_edge)
            new_w = int(pix_w * scale_ratio)
            self.setFixedSize(new_w, new_h)
        self.overlay = QtWidgets.QWidget(self)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.resize(self.size())
        self.setActive(False)
    def mousePressEvent(self, event):
        self.clicked.emit(self.page_index)
        super().mousePressEvent(event)
    def setActive(self, is_active: bool):
        if is_active:
            self.setStyleSheet("border: 3px solid #18181B; border-radius: 4px;")
            self.overlay.hide()
        else:
            self.setStyleSheet("border: 3px solid #E4E4E7; border-radius: 4px;")
            self.overlay.show()
    def resizeEvent(self, event):
        self.overlay.resize(event.size())
        super().resizeEvent(event)