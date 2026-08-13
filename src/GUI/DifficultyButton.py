from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PyQt5.QtCore import QRect, QRectF, Qt
from PyQt5.QtGui import (
	QBrush, QColor, QLinearGradient, QPainter, QPaintEvent, 
	QPalette, QPen, QRegion, QTextBlockFormat, QTextCursor, QTextDocument
)
from PyQt5.QtWidgets import (
	QButtonGroup, QGraphicsDropShadowEffect, QGridLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from Basics.BasicClass import BasicButton
	from Basics.Enums.ButtonState import ButtonState
	from Basics.Enums.Difficulty import Difficulty
else: 
	from .Basics.BasicClass import BasicButton
	from .Basics.Enums.ButtonState import ButtonState
	from .Basics.Enums.Difficulty import Difficulty

class DifficultyButton(BasicButton): 

	border_radius_percentage = 0.06
	size_percentage = 0.9

	def __init__(self, size: int, difficulty: Difficulty, level: Optional[int], parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.btn_size = size * self.size_percentage
		self.difficulty = difficulty
		self.level = "-" if level is None else str(level)
		self.document = QTextDocument()
		self.glow_effect = QGraphicsDropShadowEffect()

		self.glow_effect.setColor(QColor(255, 255, 255, 200))
		self.glow_effect.setBlurRadius(30)
		self.glow_effect.setOffset(0, 0)
		self.setGraphicsEffect(self.glow_effect)

		self.setFixedSize(size, size)
		self.setMask(QRegion(self.rect(), QRegion.RegionType.Rectangle))
		self.updateState()

	def updateState(self) -> None: 
		try: 
			if not self.isEnabled(): 
				self._current_state = ButtonState.DISABLED
				self.glow_effect.setEnabled(False)
			elif self._is_checked: 
				self._current_state = ButtonState.PRESSED
				self.glow_effect.setEnabled(True)
			elif self.underMouse(): 
				self._current_state = ButtonState.HOVER
				self.glow_effect.setEnabled(True)
			else: 
				self._current_state = ButtonState.NORMAL
				self.glow_effect.setEnabled(False)
		except AttributeError: 
			super().updateState()

		self.update()

	def _getScaledRect(self, rect: QRect, scale: float) -> QRect: 
		new_width = int(rect.width() * scale)
		new_height = int(rect.height() * scale)
		new_x = rect.x() + (rect.width() - new_width) // 2
		new_y = rect.y() + (rect.height() - new_height) // 2
		return QRect(new_x, new_y, new_width, new_height)

	def setLevel(self, level: Optional[int]) -> None: 
		self.level = "-" if level is None else str(level)
		self.updateState()

class OrdinaryButton(DifficultyButton): 

	font_size_percantage = 0.5

	def __init__(self, size: int, difficulty: Difficulty, level: int, 
			config: Dict[str, Dict[str, str]], parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(size, difficulty, level, parent)
		self.config = config

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		rect = self.rect()
		scaled_rect = self._getScaledRect(rect, self.size_percentage)

		config = self.config[self._current_state.value]
		fill_color = config["background-color"]
		border_color = config["border-color"]
		border_radius = int(self.btn_size * self.border_radius_percentage)

		painter.setBrush(QBrush(QColor(fill_color)))
		pen = QPen(QColor(border_color), border_radius, Qt.PenStyle.SolidLine)
		painter.setPen(pen)

		painter.drawEllipse(scaled_rect)

		painter.save()
		painter.setPen(QPen())
		html_text = (
			"<div style='text-align: center; font-size: {fn_size}px; font-family: {fn_family}; "
			"font-weight: {fn_weight}; font-style: {fn_style}; color: {color}'><span>{content}</span></div>"
		).format(
			fn_size = int(self.btn_size * self.font_size_percantage), 
			fn_family = self.config[self._current_state.value]["font-family"], 
			fn_weight = self.config[self._current_state.value]["font-weight"], 
			fn_style = self.config[self._current_state.value]["font-style"], 
			content = self.level, 
			color = self.config[self._current_state.value]["font-color"]
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
		doc_x = (rect.width() - doc_size.width()) / 2
		doc_y = (rect.height() - doc_size.height()) / 2
		target_rect = QRectF(doc_x, doc_y, doc_size.width(), doc_size.height())
		painter.translate(target_rect.topLeft())
		self.document.drawContents(painter, QRectF(0, 0, target_rect.width(), target_rect.height()))
		painter.restore()
		painter.end()

class AppendButton(DifficultyButton): 

	ruby_percentage = 0.6
	font_size_percantage = 0.45

	def __init__(self, size: int, difficulty: Difficulty, level: int, 
			config: Dict[str, Dict[str, Any]], parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(size, difficulty, level, parent)
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
		scaled_rect = self._getScaledRect(rect, self.size_percentage)

		config = self.config[self._current_state.value]
		fill_color = self._getColor(config["background-color"], rect)
		border_color = self._getColor(config["border-color"], rect)
		border_radius = int(self.btn_size * self.border_radius_percentage)

		painter.setBrush(QBrush(fill_color))
		pen = QPen(border_color, border_radius, Qt.PenStyle.SolidLine)
		painter.setPen(pen)

		painter.drawEllipse(scaled_rect)

		painter.save()
		painter.setPen(QPen())
		html_text = (
			"<div style='text-align: center; font-family: {fn_family}; "
			"font-weight: {fn_weight}; font-style: {fn_style}; color: {color}'><span style="
			"'font-size: {ruby_size}px'>APD</span><br><span style='font-size: {fn_size}px'>{content}</span></div>"
		).format(
			fn_size = int(self.btn_size * self.font_size_percantage), 
			ruby_size = int(self.btn_size * self.font_size_percantage * self.ruby_percentage),
			fn_family = self.config[self._current_state.value]["font-family"], 
			fn_weight = self.config[self._current_state.value]["font-weight"], 
			fn_style = self.config[self._current_state.value]["font-style"], 
			content = self.level, 
			color = self.config[self._current_state.value]["font-color"]
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
		doc_x = (rect.width() - doc_size.width()) / 2
		doc_y = (rect.height() - doc_size.height()) / 2
		painter.translate(doc_x, doc_y)
		self.document.drawContents(painter)
		painter.restore()
		painter.end()


class DifficultyButtonSet(QWidget): 

	padding = 5

	def __init__(self, 
			btn_size: int, levels: Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]], 
			btn_config: Dict[str, Dict[str, Dict[str, Any]]], 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.btn_size = btn_size
		self.setFixedHeight(btn_size + 2 * self.padding)
		level: Callable[[Optional[int]], int] = lambda level: 0 if level is None else level
		self.easy_button = OrdinaryButton(self.btn_size, Difficulty.EASY, level(levels[0]), btn_config["easy"], self)
		self.normal_button = OrdinaryButton(self.btn_size, Difficulty.NORMAL, level(levels[1]), btn_config["normal"], self)
		self.hard_button = OrdinaryButton(self.btn_size, Difficulty.HARD, level(levels[2]), btn_config["hard"], self)
		self.expert_button = OrdinaryButton(self.btn_size, Difficulty.EXPERT, level(levels[3]), btn_config["expert"], self)
		self.master_button = OrdinaryButton(self.btn_size, Difficulty.MASTER, level(levels[4]), btn_config["master"], self)
		self.append_button = AppendButton(self.btn_size, Difficulty.APPEND, level(levels[5]), btn_config["append"], self)

		self.button_group = QButtonGroup(self)
		self.my_layout = QGridLayout(self)
		self.setLayout(self.my_layout)

		self.btn_list: List[DifficultyButton] = [
			self.easy_button, self.normal_button, self.hard_button, 
			self.expert_button, self.master_button, self.append_button
		]

		for idx, btn in enumerate(self.btn_list): 
			btn.setCheckable(True)
			btn.setEnabled(levels[idx] is not None)
			self.button_group.addButton(btn)
			self.my_layout.addWidget(btn, 0, idx)

		self.button_group.setExclusive(True)
		self.easy_button.setChecked(True)

		palette = self.palette()
		color = QColor("#5c5c7d")
		color.setAlpha(127)
		palette.setColor(QPalette.ColorRole.Window, color)
		self.setPalette(palette)
		self.setAutoFillBackground(True)

	def setLevels(self, 
			levels: Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]], 
			difficulty: Difficulty
		) -> None: 
		btn_dict: Dict[Difficulty, DifficultyButton] = {
			Difficulty.EASY: self.easy_button, 
			Difficulty.NORMAL: self.normal_button, 
			Difficulty.HARD: self.hard_button, 
			Difficulty.EXPERT: self.expert_button, 
			Difficulty.MASTER: self.master_button, 
			Difficulty.APPEND: self.append_button
		}
		if all(elem is None for elem in levels): 
			for value in btn_dict.values(): 
				value.setLevel(None)
				value.setEnabled(True)
			btn_dict[difficulty].setChecked(True)
			return
		
		def setting(button: DifficultyButton, level: Optional[int]) -> None: 
			if level is None: 
				button.setEnabled(False)
			else: 
				button.setLevel(level)
				button.setEnabled(True)

		setting(self.easy_button, levels[0])
		setting(self.normal_button, levels[1])
		setting(self.hard_button, levels[2])
		setting(self.expert_button, levels[3])
		setting(self.master_button, levels[4])
		setting(self.append_button, levels[5])

		if difficulty == Difficulty.APPEND: 
			if self.append_button.isEnabled(): 
				self.append_button.setChecked(True)
			else: 
				self.easy_button.setChecked(True)
		else: 
			btn = btn_dict[difficulty]
			if btn.isEnabled(): 
				btn.setChecked(True)
			else: 
				self.append_button.setChecked(True)

	def setCheckedDifficulty(self, difficulty: Difficulty) -> None: 
		if difficulty == Difficulty.EASY and self.easy_button.isEnabled(): 
			self.easy_button.setChecked(True)
		elif difficulty == Difficulty.NORMAL and self.normal_button.isEnabled(): 
			self.normal_button.setChecked(True)
		elif difficulty == Difficulty.HARD and self.hard_button.isEnabled(): 
			self.hard_button.setChecked(True)
		elif difficulty == Difficulty.EXPERT and self.expert_button.isEnabled(): 
			self.expert_button.setChecked(True)
		elif difficulty == Difficulty.MASTER and self.master_button.isEnabled(): 
			self.master_button.setChecked(True)
		elif difficulty == Difficulty.APPEND and self.append_button.isEnabled(): 
			self.append_button.setChecked(True)

	def getDifficulty(self) -> Difficulty:
		checked_button: Optional[DifficultyButton] = self.button_group.checkedButton()
		assert checked_button is not None
		return checked_button.difficulty