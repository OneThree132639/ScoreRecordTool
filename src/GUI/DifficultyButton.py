from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import (
	QBrush, QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPaintEvent, 
	QPalette, QPen, QRegion, QTextBlockFormat, QTextCursor, QTextDocument
)
from PyQt5.QtWidgets import (
	QButtonGroup, QGraphicsDropShadowEffect, QGridLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from Basics.BasicClass import BasicButton
	from Basics.Enums.ButtonState import ButtonState
	from Basics.Enums.Difficulty import Difficulty
	from Basics.PyQt5Assistants.StrToEnum import strToFontStyle, strToFontWeight
else: 
	from .Basics.BasicClass import BasicButton
	from .Basics.Enums.ButtonState import ButtonState
	from .Basics.Enums.Difficulty import Difficulty
	from .Basics.PyQt5Assistants.StrToEnum import strToFontStyle, strToFontWeight

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

	font_size_percentage = 0.5

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
		font_size = int(self.btn_size * self.font_size_percentage)
		font = QFont()
		font.setFamily(self.config[self._current_state.value]["font-family"])
		font.setWeight(strToFontWeight(self.config[self._current_state.value]["font-weight"]))
		font.setStyle(strToFontStyle(self.config[self._current_state.value]["font-style"]))
		font.setPixelSize(font_size)
		metrics = QFontMetrics(font)
		text_height = metrics.height()
		# text_width = metrics.boundingRect(str(self.level)).width()
		text_width = metrics.horizontalAdvance(str(self.level))
		text_rect = QRect(
			int(scaled_rect.x() + (scaled_rect.width() - text_width) / 2),
			int(scaled_rect.y() + (scaled_rect.height() - text_height) / 2),
			text_width,
			text_height
		)
		painter.setFont(font)
		painter.setPen(QPen(QColor(self.config[self._current_state.value]["font-color"])))
		painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, str(self.level))
		painter.restore()

		painter.end()

class AppendButton(DifficultyButton): 

	ruby_percentage = 0.6
	font_size_percentage = 0.45
	ruby_up_percentage = 0.2
	text_down_percentage = 0.15

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
		font_size = int(self.btn_size * self.font_size_percentage)
		font = QFont()
		font.setFamily(self.config[self._current_state.value]["font-family"])
		font.setWeight(strToFontWeight(self.config[self._current_state.value]["font-weight"]))
		font.setStyle(strToFontStyle(self.config[self._current_state.value]["font-style"]))
		font.setPixelSize(font_size)
		metrics = QFontMetrics(font)
		text_height = metrics.height()
		# text_width = metrics.boundingRect(str(self.level)).width()
		text_width = metrics.horizontalAdvance(str(self.level))
		text_rect = QRect(
			int(scaled_rect.x() + (scaled_rect.width() - text_width) / 2),
			int(scaled_rect.y() + (scaled_rect.height() - text_height) / 2 + scaled_rect.height() * self.text_down_percentage),
			text_width,
			text_height
		)
		painter.setFont(font)
		painter.setPen(QPen(QColor(self.config[self._current_state.value]["font-color"])))
		painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, str(self.level))
		painter.restore()

		painter.save()
		font_size = int(self.btn_size * self.font_size_percentage * self.ruby_percentage)
		font = QFont()
		font.setFamily(self.config[self._current_state.value]["font-family"])
		font.setWeight(strToFontWeight(self.config[self._current_state.value]["font-weight"]))
		font.setStyle(strToFontStyle(self.config[self._current_state.value]["font-style"]))
		font.setPixelSize(font_size)
		metrics = QFontMetrics(font)
		text_height = metrics.height()
		# text_width = metrics.boundingRect("APD").width()
		text_width = metrics.horizontalAdvance("APD")
		text_rect = QRect(
			int(scaled_rect.x() + (scaled_rect.width() - text_width) / 2),
			int(scaled_rect.y() + (scaled_rect.height() - text_height) / 2 - scaled_rect.height() * self.ruby_up_percentage),
			text_width,
			text_height
		)
		painter.setFont(font)
		painter.setPen(QPen(QColor(self.config[self._current_state.value]["font-color"])))
		painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, "APD")
		painter.restore()
		painter.end()


class DifficultyButtonSet(QWidget): 

	padding_percentage = 0.05

	def __init__(self, 
			btn_size: int, levels: Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]], 
			btn_config: Dict[str, Dict[str, Dict[str, Any]]], 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.btn_size = btn_size
		self.padding = int(self.btn_size * self.padding_percentage)
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
		self.my_layout.setContentsMargins(self.padding, self.padding, self.padding, self.padding)
		self.setLayout(self.my_layout)

		self.btn_list: List[DifficultyButton] = [
			self.easy_button, self.normal_button, self.hard_button, 
			self.expert_button, self.master_button, self.append_button
		]

		for idx, btn in enumerate(self.btn_list): 
			btn.setCheckable(True)
			btn.setEnabled(levels[idx] is not None)
			self.button_group.addButton(btn)
			self.my_layout.addWidget(btn, 0, idx, Qt.AlignmentFlag.AlignVCenter)

		self.button_group.setExclusive(True)
		self.easy_button.setChecked(True)

		palette = self.palette()
		color = QColor("#5c5c7d")
		color.setAlpha(127)
		palette.setColor(QPalette.ColorRole.Background, color)
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

	def setForcedDifficulty(self, difficulty: Difficulty) -> None: 
		self.setLevels((None, None, None, None, None, None), difficulty)
		self.setCheckedDifficulty(difficulty)

	def getDifficulty(self) -> Difficulty:
		checked_button: Optional[DifficultyButton] = self.button_group.checkedButton()
		assert checked_button is not None
		return checked_button.difficulty