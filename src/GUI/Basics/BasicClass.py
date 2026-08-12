from typing import List, Optional

from PyQt5.QtCore import (
	pyqtSignal, QEvent, QPoint, QRect, QRectF, Qt
)
from PyQt5.QtGui import (
	QBrush, QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap, 
	QRegion, QTextDocument, QTextOption
)
from PyQt5.QtWidgets import (
	QButtonGroup, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, 
	QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from Enums.ButtonState import ButtonState
else: 
	from .Enums.ButtonState import ButtonState

class BasicButton(QPushButton): 

	def __init__(self, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self._current_state = ButtonState.NORMAL
		self._is_checked = False

		self.setMouseTracking(True)
		self.toggled.connect(self._onToggled)

	def enterEvent(self, event: QEvent) -> None: 
		super().enterEvent(event)
		self.updateState()

	def leaveEvent(self, event: QEvent) -> None: 
		super().leaveEvent(event)
		self.updateState()

	def mousePressEvent(self, event: QMouseEvent) -> None: 
		super().mousePressEvent(event)
		self.updateState()

	def mouseReleaseEvent(self, event: QMouseEvent) -> None: 
		super().mouseReleaseEvent(event)
		self.updateState()

	def changeEvent(self, event: QEvent) -> None: 
		super().changeEvent(event)
		self.updateState()

	def updateState(self) -> None: 
		if not self.isEnabled(): 
			self._current_state = ButtonState.DISABLED
		elif self._is_checked: 
			self._current_state = ButtonState.PRESSED
		elif self.underMouse(): 
			self._current_state = ButtonState.HOVER
		else: 
			self._current_state = ButtonState.NORMAL

		self.update()

	def _onToggled(self, checked: bool) -> None: 
		self._is_checked = checked
		self.updateState()

def get_round_rect_pixmap(width: int, height: int, background_color: QColor, text: str) -> QPixmap: 
	pixmap = QPixmap(width, height)
	pixmap.fill(Qt.GlobalColor.transparent)

	painter = QPainter(pixmap)
	painter.setRenderHint(QPainter.RenderHint.Antialiasing)
	painter.setPen(Qt.PenStyle.NoPen)
	painter.setBrush(QBrush(background_color))
	shorter = min(width, height)
	radius = int(shorter // 2)
	painter.drawRoundedRect(0, 0, width, height, radius, radius, Qt.SizeMode.AbsoluteSize)

	painter.setPen(QPen(Qt.GlobalColor.black))
	painter.setBrush(Qt.BrushStyle.NoBrush)
	font = QFont("FOT-RodinNTLG Pro", int(shorter * 0.4))
	painter.setFont(font)
	painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
	painter.end()
	return pixmap

class GeneralClickButton(QPushButton): 

	def __init__(self, width: int, height: int, background_color: QColor, text: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.setFixedSize(width, height)
		self.pixmap = get_round_rect_pixmap(width, height, background_color, text)

		self.glow_effect = QGraphicsDropShadowEffect()

		self.glow_effect.setColor(QColor(0, 0, 0, 200))
		self.glow_effect.setBlurRadius(30)
		self.glow_effect.setOffset(0, 0)
		self.setGraphicsEffect(self.glow_effect)
		self.glow_effect.setEnabled(True)

	def paintEvent(self, event: QEvent) -> None: 
		painter = QPainter(self)
		painter.drawPixmap(0, 0, self.pixmap)
		painter.end()

class OptionButton(BasicButton): 

	btn_percentage = 0.8
	highlight_percentage = 0.5
	checked_color = "#77EEDD"

	def __init__(self, fixed_size: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.fixed_size = fixed_size
		self.btn_size = int(self.fixed_size * self.btn_percentage)
		self.highlight_size = int(self.fixed_size * self.highlight_percentage)
		self.setFixedSize(self.fixed_size, self.fixed_size)
		self.setEnabled(True)
		self.setCheckable(True)

		self.glow_effect = QGraphicsDropShadowEffect()

		self.glow_effect.setColor(QColor(0, 0, 0, 200))
		self.glow_effect.setBlurRadius(30)
		self.glow_effect.setOffset(0, 0)
		self.setGraphicsEffect(self.glow_effect)
		self.glow_effect.setEnabled(True)

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		rect = self.rect()

		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(QBrush(QColor("#FFFFFF")))
		btn_x = rect.x() + (rect.width() - self.btn_size) / 2
		btn_y = rect.y() + (rect.height() - self.btn_size) / 2
		painter.drawEllipse(QRectF(btn_x, btn_y, self.btn_size, self.btn_size))

		if self._current_state in (ButtonState.HOVER, ButtonState.PRESSED): 
			painter.setBrush(QBrush(QColor(self.checked_color)))
			highlight_x = rect.x() + (rect.width() - self.highlight_size) / 2
			highlight_y = rect.y() + (rect.height() - self.highlight_size) / 2
			painter.drawEllipse(QRectF(highlight_x, highlight_y, self.highlight_size, self.highlight_size))

		painter.end()

class OptionColumn(QWidget): 

	padding = 2
	font_size_percentage = 0.67

	enabled_color = "#000000"
	disabled_color = "#808080"

	def __init__(self, fixed_height: int, column_text: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.fixed_height = fixed_height
		self.font_size = int(self.fixed_height * self.font_size_percentage)
		self.column_text = column_text
		self.document = QTextDocument()

		self.setFixedHeight(self.fixed_height)

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

		painter.setPen(QPen())
		color = self.enabled_color if self.isEnabled() else self.disabled_color
		html_text = (
			"<span style=\"font-size: {}px; font-family: FOT-RodinNTLG Pro; color: {}; \">"
			"{}</span>"
		).format(self.font_size, color, self.column_text) 
		self.document.setHtml(html_text)
		target_rect = QRectF(self.padding, self.padding, self.width() - 2 * self.padding, self.height() - 2 * self.padding)
		self.document.drawContents(painter, target_rect)

		painter.setBrush(QBrush(QColor(color)))
		painter.drawLine(self.padding, self.fixed_height - self.padding, self.width() - self.padding, self.fixed_height - self.padding)

		painter.end()

class OptionLabel(QLabel): 

	font_name = "nintendo_NTLG-DB_001"
	max_font_size_percentage = 0.5
	num_iter = 15
	enabled_color = "#000000"
	disabled_color = "#808080"

	def __init__(self, fixed_height: int, text: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.fixed_height = fixed_height
		self.fixed_width = fixed_height * 3
		self.max_font_size = int(fixed_height * self.max_font_size_percentage)
		self.my_text = text
		self.setFixedSize(self.fixed_width, self.fixed_height)
		self.best_size = self._fitText(self.rect())

	def setText(self, text: str) -> None: 
		self.my_text = text
		self.best_size = self._fitText(self.rect())
		self.update()

	def _fitText(self, rect: QRect) -> int: 
		if not self.my_text: 
			return 0

		min_size = 1
		max_size = min(rect.width(), self.max_font_size)
		best_size = min_size

		i = 0
		while min_size < max_size and i < self.num_iter: 
			mid_size = (min_size + max_size) // 2
			font = QFont(self.font_name, mid_size)
			doc = QTextDocument()
			doc.setDefaultFont(font)
			doc.setPlainText(self.my_text)
			doc.setTextWidth(rect.width())
			option = QTextOption()
			option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
			doc.setDefaultTextOption(option)
			fits = (doc.size().height() <= rect.height())

			if fits: 
				best_size = mid_size
				min_size = mid_size + 1
			else: 
				max_size = mid_size - 1
			i += 1

		return best_size

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self) 
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		rect = self.rect()
		font = QFont(self.font_name, self.best_size)
		color = self.enabled_color if self.isEnabled() else self.disabled_color
		painter.setPen(QPen(QColor(color)))
		painter.setBrush(Qt.BrushStyle.NoBrush)
		painter.setFont(font)
		painter.drawText(rect, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.my_text)
		painter.end()

class OptionUnit(QWidget): 

	spacing = 5

	def __init__(self, fixed_height: int, text: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.option_button = OptionButton(fixed_height, self)
		self.option_label = OptionLabel(fixed_height, text, self)
		self.my_layout = QHBoxLayout(self)
		self.my_layout.setSpacing(self.spacing)
		self.my_layout.addWidget(self.option_button)
		self.my_layout.addWidget(self.option_label)

class OptionButtonSet(QWidget): 

	num_cols = 3

	def __init__(self, fixed_height: int, option_texts: List[str], default_option: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		default_index = option_texts.index(default_option) if default_option in option_texts else 0
		self.option_units = [OptionUnit(fixed_height, text, self) for text in option_texts]
		self.my_layout = QGridLayout(self)
		self.button_group = QButtonGroup(self)
		for i, option_unit in enumerate(self.option_units):
			self.my_layout.addWidget(option_unit, i // self.num_cols, i % self.num_cols)
			self.button_group.addButton(option_unit.option_button)

		self.option_units[default_index].option_button.setChecked(True)
		self.button_group.setExclusive(True)

	def getCurrentOption(self) -> str: 
		for option_unit in self.option_units: 
			if option_unit.option_button.isChecked(): 
				return option_unit.option_label.my_text
		return ""

	def setCurrentOption(self, option: str) -> None: 
		for option_unit in self.option_units: 
			if option_unit.option_label.my_text == option: 
				option_unit.option_button.setChecked(True)
				return

class OptionButtonSetWidget(QWidget): 

	button_clicked = pyqtSignal(str)

	def __init__(self, fixed_height: int, option_title: str, option_list: List[str], default_option: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.option_column = OptionColumn(fixed_height, option_title, self)
		self.option_button_set = OptionButtonSet(fixed_height, option_list, default_option, self)
		self.my_layout = QVBoxLayout(self)
		self.my_layout.addWidget(self.option_column)
		self.my_layout.addWidget(self.option_button_set)
		self.my_layout.setSpacing(0)
		self.setLayout(self.my_layout)

		self.option_button_set.button_group.buttonClicked.connect(self._onButtonClicked)

	def getCurrentOption(self) -> str: 
		return self.option_button_set.getCurrentOption()

	def setCurrentOption(self, option: str) -> None: 
		self.option_button_set.setCurrentOption(option)

	def _onButtonClicked(self) -> None: 
		self.button_clicked.emit(self.getCurrentOption())

class OptionLineEdit(QLineEdit): 

	fixed_height_percentage = 0.8
	fixed_width_percentage = 1.6

	def __init__(self, fixed_height: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.fixed_height = int(fixed_height * self.fixed_height_percentage)
		self.fixed_width = int(self.fixed_height * self.fixed_width_percentage)
		self.setFixedSize(self.fixed_width, self.fixed_height)

		self.glow_effect = QGraphicsDropShadowEffect()

		self.glow_effect.setColor(QColor(0, 0, 0, 200))
		self.glow_effect.setBlurRadius(30)
		self.glow_effect.setOffset(0, 0)
		self.setGraphicsEffect(self.glow_effect)
		self.glow_effect.setEnabled(True)

		self.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.setStyleSheet(
			"QLineEdit {\n"
			"\tbackground-color: #FFFFFF; \n"
			"\tcolor: #000000; \n"
			"\tborder: 1px solid gray; \n"
			"\tborder radius: 10px; \n"
			"\tfont-family: nintendo_NTLG-DB_001; \n"
			"\tfont-size: 15px; \n"
			"}"
			"QLineEdit:focus {\n"
			"\tborder: 1px solid skyblue; \n"
			"}"
		)

class OptionCheckBoxIndicator(BasicButton): 

	fixed_size_percentage = 0.75
	round_radius = 5
	checked_tick_color = "#FF77AA"
	disabled_color = "#808080"

	def __init__(self, fixed_size: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.fixed_size = int(fixed_size * self.fixed_size_percentage)
		self.setFixedSize(self.fixed_size, self.fixed_size)
		self.setMask(QRegion(self.rect(), QRegion.RegionType.Rectangle))
		self.setEnabled(True)
		self.setCheckable(True)

		self.glow_effect = QGraphicsDropShadowEffect()

		self.glow_effect.setColor(QColor(0, 0, 0, 200))
		self.glow_effect.setBlurRadius(30)
		self.glow_effect.setOffset(0, 0)
		self.setGraphicsEffect(self.glow_effect)
		self.glow_effect.setEnabled(True)

	def updateState(self) -> None: 
		if not self.isEnabled(): 
			if self._current_state in (ButtonState.PRESSED, ButtonState.DISABLED_PRESSED): 
				self._current_state = ButtonState.DISABLED_PRESSED
			else: 
				self._current_state = ButtonState.DISABLED
		elif self._is_checked: 
			self._current_state = ButtonState.PRESSED
		elif self.underMouse(): 
			self._current_state = ButtonState.HOVER
		else: 
			self._current_state = ButtonState.NORMAL

		self.update()

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		rect = self.rect()

		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(QBrush(QColor("#FFFFFF")))
		painter.drawRoundedRect(rect, self.round_radius, self.round_radius)

		if self._current_state in (ButtonState.PRESSED, ButtonState.DISABLED_PRESSED): 
			color = QColor(self.checked_tick_color) if self._current_state != ButtonState.DISABLED_PRESSED else QColor(self.disabled_color)
			painter.setPen(QPen(QColor(color), self.fixed_size * 0.2))
			calc_x = lambda x: int(rect.x() + x * rect.width())
			calc_y = lambda y: int(rect.y() + y * rect.height())
			start = QPoint(calc_x(0.2), calc_y(0.5))
			turn = QPoint(calc_x(0.4), calc_y(0.8))
			end = QPoint(calc_x(0.8), calc_y(0.2))
			painter.drawLine(start, turn)
			painter.drawLine(turn, end)

		painter.end()

class OptionCheckBox(QWidget): 

	spacing = 20

	def __init__(self, fixed_height: int, text: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.checkbox_indicator = OptionCheckBoxIndicator(fixed_height, self)
		self.option_label = OptionLabel(fixed_height, text, self)
		self.my_layout = QHBoxLayout(self)
		self.my_layout.setSpacing(self.spacing)
		self.my_layout.addWidget(self.checkbox_indicator)
		self.my_layout.addWidget(self.option_label)
		self.setLayout(self.my_layout)

	def getText(self) -> str: 
		return self.option_label.my_text

	def isChecked(self) -> bool: 
		return self.checkbox_indicator.isChecked()

	def setChecked(self, checked: bool) -> None: 
		self.checkbox_indicator.setChecked(checked)

	def setEnabled(self, enabled: bool) -> None: 
		super().setEnabled(enabled)
		self.checkbox_indicator.setEnabled(enabled)

class OptionCheckBoxSet(QWidget): 

	num_col = 3

	def __init__(self, fixed_size: int, option_texts: List[str], default_options: List[str]=[], parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.option_checkboxes = [OptionCheckBox(fixed_size, text, self) for text in option_texts]
		self.my_layout = QGridLayout(self)
		for idx, option_checkbox in enumerate(self.option_checkboxes): 
			option_checkbox.setEnabled(True)
			option_checkbox.setChecked(False)
			if option_checkbox.getText() in default_options:
				option_checkbox.setChecked(True)
			self.my_layout.addWidget(option_checkbox, idx // self.num_col, idx % self.num_col)
		self.setLayout(self.my_layout)

	def getCurrentOptions(self) -> List[str]: 
		return [checkbox.getText() for checkbox in self.option_checkboxes if checkbox.isChecked()]

	def setCurrentOptions(self, options: List[str]) -> None: 
		for checkbox in self.option_checkboxes: 
			checkbox.setChecked(checkbox.getText() in options)

	def setEnabled(self, enabled: bool) -> None: 
		super().setEnabled(enabled)
		for checkbox in self.option_checkboxes: 
			checkbox.setEnabled(enabled)

class OptionCheckBoxSetWidget(QWidget): 

	def __init__(self, fixed_size: int, 
			option_title: str, option_list: List[str], 
			default_options: List[str] = [], parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.option_column = OptionColumn(fixed_size, option_title, self)
		self.option_checkbox_set = OptionCheckBoxSet(fixed_size, option_list, default_options, self)
		self.my_layout = QVBoxLayout(self)
		self.my_layout.addWidget(self.option_column)
		self.my_layout.addWidget(self.option_checkbox_set)
		self.my_layout.setSpacing(0)
		self.setLayout(self.my_layout)

	def getCurrentOptions(self) -> List[str]: 
		return self.option_checkbox_set.getCurrentOptions()

	def setCurrentOptions(self, options: List[str]) -> None: 
		self.option_checkbox_set.setCurrentOptions(options)

	def setEnabled(self, enabled: bool) -> None: 
		super().setEnabled(enabled)
		self.option_column.setEnabled(enabled)
		self.option_checkbox_set.setEnabled(enabled)