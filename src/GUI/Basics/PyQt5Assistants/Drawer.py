from PyQt5.QtCore import (
	QRect, Qt
)
from PyQt5.QtGui import (
	QBrush, QColor, QPainter, QPen
)

def drawRect(painter: QPainter, rect: QRect, color: QColor, pen_width: int) -> None: 
	painter.save()
	pen = QPen()
	pen.setColor(color)
	pen.setWidth(pen_width)
	pen.setStyle(Qt.PenStyle.SolidLine)
	painter.setPen(pen)
	painter.setBrush(Qt.BrushStyle.NoBrush)
	painter.drawRect(rect)
	painter.restore()