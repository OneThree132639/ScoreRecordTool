from typing import Any, Dict, List, Optional, Union

from PyQt5.QtCore import (
	QPointF, QRect, QRectF, Qt, QTimer
)
from PyQt5.QtGui import (
	QBrush, QColor, QFont, QFontMetrics, QLinearGradient, 
	QPainter, QPainterPath, QPainterPathStroker, QPaintEvent, 
	QPen, QTextBlockFormat, QTextCursor, QTextDocument
)
from PyQt5.QtWidgets import (
	QLabel, QSizePolicy, QWidget
)

if __package__ is None or __package__ == "": 
	from Enums.Difficulty import Difficulty
	from PyQt5Assistants.StrToEnum import (
		strToFontStyle, strToFontWeight
	)
else: 
	from .Enums.Difficulty import Difficulty
	from .PyQt5Assistants.StrToEnum import (
		strToFontStyle, strToFontWeight
	)

class MarqueeLabel(QLabel): 

	scroll_interval = 10
	pause_duration = 1500

	def __init__(self, text: str, font_name: str, font_size: int, debug: bool, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.setText(text)
		self.setWordWrap(False)
		self.debug = debug

		font = QFont()
		font.setFamily(font_name)
		font.setPointSize(font_size)
		self.setFont(font)

		self.offset = 0
		self.timer = QTimer(self)
		self.timer.setInterval(self.scroll_interval)
		self.timer.timeout.connect(self.updateOffset)
		self.is_paused = False

		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

	def updateOffset(self) -> None: 
		if self.is_paused: 
			return
		
		metrics = QFontMetrics(self.font())
		text_width = metrics.horizontalAdvance(self.text())

		if text_width <= self.width(): 
			self.offset = 0
			self.timer.stop()
			return

		self.offset -= 1
		if self.offset == 0: 
			self.is_paused = True
			QTimer.singleShot(self.pause_duration, self.resumeScrolling)
		if self.offset < -text_width: 
			self.offset = self.width()

		self.update()

	def resumeScrolling(self) -> None: 
		self.is_paused = False
		self.update()

	def _getTextWidth(self) -> int: 
		metrics = QFontMetrics(self.font())
		return metrics.horizontalAdvance(self.text())

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		painter.setFont(self.font())
		painter.setPen(self.palette().text().color())

		text_width = self._getTextWidth()
		if text_width <= self.width(): 
			painter.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())
		else: 
			x = self.offset
			painter.drawText(self.rect().adjusted(x, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())

	def pause(self) -> None: 
		self.timer.stop()
		self.offset = 0

	def resume(self) -> None: 
		self.is_paused = True
		QTimer.singleShot(self.pause_duration, self.resumeScrolling)
		self.timer.start()

class LevelLabel(QLabel): 

	size_percentage = 0.85
	normal_percentage = 0.8
	special_text_font_size_percentage = 0.22
	special_text_border_size_percentage = 0.1
	special_text_height_percentage = -0.02

	def __init__(self, 
			level: int, is_special: bool, label_size: int, 
			difficluty: Difficulty, parent: Optional[QWidget]=None
		): 
		super().__init__(parent)
		self.level = level
		self.is_special = is_special
		self.label_size = label_size
		self.difficulty = difficluty
		self.special_percentage = 1.0 if is_special else self.normal_percentage
		self.document = QTextDocument()
		self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

		self.setFixedSize(self.label_size, self.label_size)

	def _getScaledRect(self, rect: QRect, scale: float) -> QRect: 
		new_width = int(rect.width() * scale)
		new_height = int(rect.height() * scale)
		new_x = rect.x() + (rect.width() - new_width) // 2
		new_y = rect.y() + (rect.height() - new_height) // 2
		return QRect(new_x, new_y, new_width, new_height)

	def _drawSpecialText(self, painter: QPainter, rect: QRect) -> None: 
		path = QPainterPath()
		font = QFont()
		font.setFamily("FOT-RodinNTLG Pro")
		font.setWeight(QFont.Weight.Black)
		font.setPointSizeF(self.label_size * self.special_text_font_size_percentage)
		path.addText(QPointF(0, 0), font, "楽曲Lv.")

		bounding_rect = path.boundingRect()
		target_x = rect.x() + (rect.width() - bounding_rect.width()) // 2
		target_y = rect.y() + rect.height() * self.special_text_height_percentage
		offset_x = target_x - bounding_rect.x()
		offset_y = target_y - bounding_rect.y()
		path.translate(offset_x, offset_y)

		stroker = QPainterPathStroker()
		stroker.setWidth(self.label_size * self.special_text_border_size_percentage)
		stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
		stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
		stroker_path = stroker.createStroke(path)

		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(QBrush(QColor("#828299")))
		painter.drawPath(stroker_path)
		
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(QBrush(QColor("#FFFFFF")))
		painter.drawPath(path)

class OrdinaryLabel(LevelLabel): 

	font_size_percantage = 0.43

	def __init__(self, level: int, is_special: bool, label_size: int, 
			difficulty: Difficulty, config: Dict[str, str], 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(level, is_special, label_size, difficulty, parent)
		self.config = config

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		rect = self.rect()
		scaled_rect = self._getScaledRect(rect, self.size_percentage * self.special_percentage)

		fill_color = self.config["background-color"]
		painter.setBrush(QBrush(QColor(fill_color)))
		painter.setPen(Qt.PenStyle.NoPen)
		painter.drawEllipse(scaled_rect)

		painter.save()
		font_size = int(self.label_size * self.font_size_percantage * self.special_percentage)
		font = QFont()
		font.setFamily(self.config["font-family"])
		font.setWeight(strToFontWeight(self.config["font-weight"]))
		font.setStyle(strToFontStyle(self.config["font-style"]))
		font.setPixelSize(font_size)
		metrics = QFontMetrics(font)
		text_height = metrics.height()
		text_width = metrics.width(str(self.level))
		text_rect = QRect(
			int(scaled_rect.x() + (scaled_rect.width() - text_width) / 2),
			int(scaled_rect.y() + (scaled_rect.height() - text_height) / 2),
			text_width,
			text_height
		)
		painter.setFont(font)
		painter.setPen(QPen(QColor(self.config["font-color"])))
		painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, str(self.level))
		painter.restore()

		if self.is_special: 
			painter.save()
			self._drawSpecialText(painter, scaled_rect)
			painter.restore()

		painter.end()

class AppendLabel(LevelLabel): 

	ruby_percentage = 0.6
	font_size_percantage = 0.35
	text_down_percentage = 0.05
	special_append_percentage = 0.95

	def __init__(self, level: int, is_special: bool, label_size: int, 
			difficulty: Difficulty, config: Dict[str, Any], 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(level, is_special, label_size, difficulty, parent)
		self.config = config

	def _getColor(self, entry: Union[str, List[str]], rect: QRect) -> Union[QColor, QLinearGradient]: 
		if isinstance(entry, str): 
			return QColor(entry)
		elif isinstance(entry, list): 
			if len(entry) == 2: 
				color = QLinearGradient(rect.topLeft(), rect.bottomRight())
				color.setColorAt(0, QColor(entry[0]))
				color.setColorAt(1, QColor(entry[1]))
				return color
			else: 
				return QColor(entry[0])
		else: 
			raise ValueError("Invalid color entry: {}".format(entry))

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		rect = self.rect()
		scaled_rect = self._getScaledRect(rect, self.size_percentage * self.special_percentage)

		fill_color = self._getColor(self.config["background-color"], rect)
		painter.setBrush(QBrush(fill_color))
		painter.setPen(Qt.PenStyle.NoPen)
		painter.drawEllipse(scaled_rect)

		scale = self.special_append_percentage if self.is_special else 1
		basic_font_size = self.label_size * self.font_size_percantage * self.special_percentage * scale
		painter.save()
		painter.setPen(QPen())
		html_text = (
			"<div style='text-align: center; font-family: {fn_family}; "
			"font-weight: {fn_weight}; font-style: {fn_style}; color: {color}'><span style="
			"'font-size: {ruby_size}pt'>APD</span><br><span style='font-size: {fn_size}pt'>{content}</span></div>"
		).format(
			fn_size = int(basic_font_size), 
			ruby_size = int(basic_font_size * self.ruby_percentage),
			fn_family = self.config["font-family"], 
			fn_weight = self.config["font-weight"], 
			fn_style = self.config["font-style"], 
			content = self.level, 
			color = self.config["font-color"]
		)
		self.document.setHtml(html_text)
		cursor = QTextCursor(self.document)
		while True: 
			block_format = cursor.blockFormat()
			block_format.setTopMargin(0)
			block_format.setBottomMargin(0)
			block_format.setLineHeight(50, QTextBlockFormat.LineHeightTypes.ProportionalHeight)
			cursor.setBlockFormat(block_format)
			if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock): 
				break

		self.document.setTextWidth(self.width())
		doc_size = self.document.size()
		down_offset = self.text_down_percentage * self.label_size if self.is_special else 0
		doc_x = (rect.width() - doc_size.width()) / 2
		doc_y = (rect.height() - doc_size.height()) / 2 + down_offset
		painter.translate(doc_x, doc_y)
		self.document.drawContents(painter)
		painter.restore()

		if self.is_special: 
			painter.save()
			self._drawSpecialText(painter, scaled_rect)
			painter.restore()

		painter.end()