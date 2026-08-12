import numpy as np

from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import (
	pyqtSignal, Qt
)
from PyQt5.QtGui import (
	QColor, QFont, QImage, QIntValidator, QPainter, QPaintEvent, QPalette, QPixmap
)
from PyQt5.QtWidgets import (
	QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from Basics.BasicClass import (
		GeneralClickButton, OptionButtonSetWidget, 
		OptionCheckBoxSetWidget, OptionColumn, OptionLineEdit
	)
else: 
	from .Basics.BasicClass import (
		GeneralClickButton, OptionButtonSetWidget, 
		OptionCheckBoxSetWidget, OptionColumn, OptionLineEdit
	)

class RandomButton(QPushButton): 

	btn_size_percentage = 0.8

	def __init__(self, init_height: int,  icon_array: np.ndarray, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.init_height = init_height
		self.btn_size = int(self.init_height * self.btn_size_percentage)
		self.setFixedSize(self.btn_size, self.btn_size)
		self.my_mask = icon_array
		self.pixmap = self._generatePixmap()

	def _generatePixmap(self) -> QPixmap: 
		color = QColor(255, 255, 255, 255)
		rgba_array = np.zeros((self.my_mask.shape[0], self.my_mask.shape[1], 4), dtype=np.uint8)

		rgba_array[self.my_mask, 0] = color.red()
		rgba_array[self.my_mask, 1] = color.green()
		rgba_array[self.my_mask, 2] = color.blue()
		rgba_array[self.my_mask, 3] = color.alpha()

		image = QImage( 
			rgba_array.data, rgba_array.shape[1], rgba_array.shape[0], # type: ignore
			rgba_array.shape[1]*4, QImage.Format.Format_RGBA8888
		) 
		pixmap = QPixmap.fromImage(image.copy())

		pixmap = pixmap.scaled(self.btn_size, self.btn_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

		return pixmap

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		rect = self.rect()
		painter.drawPixmap(rect, self.pixmap)

class RandomLevelWidget(QWidget): 

	valid_min_level = 5
	valid_max_level = 38
	spacing = 5

	def __init__(self, min_level: int=5, max_level: int=38, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.title = OptionColumn("レベル", self)
		self.min_level = OptionLineEdit(self)
		self.max_level = OptionLineEdit(self)
		self.hash_label = QLabel("-", self)
		font = QFont("nintendo_NTLG-DB_001", 20)
		self.hash_label.setFont(font)
		self.hash_label.setFixedWidth(20)
		self.hash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.level_widget = QWidget(self)
		self.level_layout = QHBoxLayout(self.level_widget)
		self.level_layout.addWidget(self.min_level)
		self.level_layout.addWidget(self.hash_label)
		self.level_layout.addWidget(self.max_level)
		self.level_layout.setSpacing(self.spacing)

		self.my_layout = QVBoxLayout(self)
		self.my_layout.addWidget(self.title)
		self.my_layout.addWidget(self.level_widget)
		self.my_layout.setSpacing(self.spacing)

		min_validator = QIntValidator(self.valid_min_level, self.valid_max_level, self)
		max_validator = QIntValidator(self.valid_min_level, self.valid_max_level, self)
		self.min_level.setValidator(min_validator)
		self.max_level.setValidator(max_validator)
		self.min_level.setText(str(min_level))
		self.max_level.setText(str(max_level))

		self.min_level.editingFinished.connect(self._onMinLevelFinished)
		self.max_level.editingFinished.connect(self._onMaxLevelFinished)

	def _onMinLevelFinished(self) -> None:
		text = self.min_level.text()
		if text == "": 
			self.min_level.setText(str(self.valid_min_level))
			return
		try: 
			level = int(text)
			if level < self.valid_min_level: 
				self.min_level.setText(str(self.valid_max_level))
			elif level > int(self.max_level.text()): 
				self.min_level.setText(self.max_level.text())
		except ValueError: 
			self.min_level.setText(str(self.valid_min_level))

	def _onMaxLevelFinished(self) -> None: 
		text = self.max_level.text() 
		if text == "": 
			self.max_level.setText(str(self.valid_max_level))
			return
		try: 
			level = int(text)
			if level > self.valid_max_level: 
				self.max_level.setText(str(self.valid_max_level))
			elif level < int(self.min_level.text()): 
				self.max_level.setText(self.min_level.text())
		except ValueError: 
			self.max_level.setText(str(self.valid_max_level))

	def getCurrentLevelRange(self) -> Tuple[int, int]: 
		try: 
			min_level = int(self.min_level.text())
		except ValueError: 
			min_level = self.valid_min_level
		try: 
			max_level = int(self.max_level.text())
		except ValueError: 
			max_level = self.valid_max_level
		return (min_level, max_level)

	def getCurrentLevelRangeConfig(self) -> Dict[str, int]: 
		min_level, max_level = self.getCurrentLevelRange()
		return {
			"min_level": min_level, 
			"max_level": max_level
		}

	def setCurrentLevelRange(self, min_level: int, max_level: int) -> None: 
		self.min_level.setText(str(min_level))
		self.max_level.setText(str(max_level))
		
class RandomDialog(QDialog): 

	button_width = 120
	button_height = 40

	def __init__(self, default_option: Dict[str, Any]={}, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.my_layout = QVBoxLayout(self)
		self.setLayout(self.my_layout)

		self.song_range = OptionButtonSetWidget(
			"難易度", ["現在の難易度", "複数の難易度"], default_option.get("song_range", "現在の難易度"), self
		)
		self.difficulty_checkbox_set = OptionCheckBoxSetWidget(
			"難易度選択", ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"], 
			default_options=default_option.get("difficulty_checkbox_set", []), parent=self
		)
		self._onSongRangeButtonClicked(self.song_range.getCurrentOption())
		level_range = default_option.get("level_widget", (5, 38))
		self.level_widget = RandomLevelWidget(
			level_range[0], level_range[1], 
			parent=self
		)

		self.cancel_button = GeneralClickButton(self.button_width, self.button_height, QColor(255, 255, 255), "キャンセル", self)
		self.accept_button = GeneralClickButton(self.button_width, self.button_height, QColor("#77EEDD"), "決定", self)
		self.cancel_button.clicked.connect(self.reject)
		self.accept_button.clicked.connect(self.accept)
		self.button_layout = QHBoxLayout()
		self.button_layout.addWidget(self.cancel_button)
		self.button_layout.addWidget(self.accept_button)
		self.button_layout.setSpacing(10)
		self.button_widget = QWidget()
		self.button_widget.setLayout(self.button_layout)

		self.my_layout.addWidget(self.song_range)
		self.my_layout.addWidget(self.difficulty_checkbox_set)
		self.my_layout.addWidget(self.level_widget)
		self.my_layout.addWidget(self.button_widget)

		self.song_range.button_clicked.connect(self._onSongRangeButtonClicked)

	def getCurrentOptions(self) -> Tuple[str, List[str], Tuple[int, int]]: 
		return (
			self.song_range.getCurrentOption(), 
			self.difficulty_checkbox_set.getCurrentOptions(), 
			self.level_widget.getCurrentLevelRange()
		)

	def getCurrentOptionsConfig(self) -> Dict[str, Any]: 
		return {
			"song_range": self.song_range.getCurrentOption(), 
			"difficulty_checkbox_set": self.difficulty_checkbox_set.getCurrentOptions(), 
			"level_widget": self.level_widget.getCurrentLevelRange()
		}

	def setCurrentOptions(self, options: Tuple[str, List[str], Tuple[int, int]]) -> None: 
		song_range_option, difficulty_options, level_range = options
		self.song_range.setCurrentOption(song_range_option)
		self.difficulty_checkbox_set.setCurrentOptions(difficulty_options)
		self.level_widget.setCurrentLevelRange(level_range[0], level_range[1])

	def _onSongRangeButtonClicked(self, name: str) -> None: 
		if name == "現在の難易度": 
			self.difficulty_checkbox_set.setEnabled(False)
		elif name == "複数の難易度": 
			self.difficulty_checkbox_set.setEnabled(True)

	def exec(self) -> int: 
		self._onSongRangeButtonClicked(self.song_range.getCurrentOption())
		return super().exec()


class RandomWidget(QWidget): 

	option_changed = pyqtSignal()

	def __init__(self, init_height: int, 
			get_icon_func: Callable[[str], np.ndarray], default_option: Dict[str, Any]={}, 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.init_height = init_height
		self.get_icon_func = get_icon_func
		self.random_button = RandomButton(self.init_height, self.get_icon_func("random-icon-array"), self)
		self.setting_button = RandomButton(self.init_height, self.get_icon_func("random-setting-array"), self)
		self.setting_dialog = RandomDialog(default_option, self)
		self.my_layout = QHBoxLayout(self)
		self.my_layout.addWidget(self.random_button)
		self.my_layout.addWidget(self.setting_button)
		self.my_layout.setSpacing(50)
		self.setLayout(self.my_layout)
		self.setFixedHeight(self.init_height)

		palette = self.palette()
		color = QColor("#5c5c7d")
		color.setAlpha(127)
		palette.setColor(QPalette.ColorRole.Window, color)
		self.setPalette(palette)
		self.setAutoFillBackground(True)

		self.setting_button.clicked.connect(self._onSettingClicked)

	def _onSettingClicked(self) -> None: 
		current_options = self.setting_dialog.getCurrentOptions()

		if self.setting_dialog.exec() == QDialog.DialogCode.Accepted: 
			self.option_changed.emit()
		else: 
			self.setting_dialog.setCurrentOptions(current_options)