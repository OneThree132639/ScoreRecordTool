from typing import Any, Dict, Optional, Tuple

from PyQt5.QtCore import (
	pyqtSignal, Qt
)
from PyQt5.QtGui import (
	QBrush, QColor, QPainter, QPaintEvent, QPainterPath, QPixmap
)
from PyQt5.QtWidgets import (
	QDialog, QGraphicsDropShadowEffect, 
	QHBoxLayout, QPushButton, QVBoxLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from Basics.Enums.FilterOptions import SongType, Timeline
	from Basics.BasicClass import (
		GeneralClickButton, OptionButtonSetWidget, OptionCheckBoxSetWidget
	)
else: 
	from .Basics.Enums.FilterOptions import SongType, Timeline
	from .Basics.BasicClass import (
		GeneralClickButton, OptionButtonSetWidget, OptionCheckBoxSetWidget
	)

class FilterButton(QPushButton): 

	normal_color = "#444466"
	abnormal_color = "#FF77AA"

	filter_option_changed = pyqtSignal()

	def __init__(self, 
			default_options: Dict[str, Any], btn_size: int, 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)

		self.btn_size = btn_size
		self._is_normal = True
		self._bound_path = self._boundPath()
		self._filter_path = self._filterPath()
		self._normal_pixmap = self._filterPixmap(self.normal_color)
		self._abnormal_pixmap = self._filterPixmap(self.abnormal_color)
		self.filter_dialog = FilterDialog(btn_size, default_options, self)

		self.setFixedSize(btn_size, btn_size)
		self.setStyleSheet((
			"QPushButton {"
			"\tborder: 0px; "
			"\toutline: none; "
			"}"
		))

		self.glow_effect = QGraphicsDropShadowEffect()
		self.glow_effect.setColor(QColor(255, 255, 255, 200))
		self.glow_effect.setBlurRadius(30)
		self.glow_effect.setOffset(0, 0)
		self.setGraphicsEffect(self.glow_effect)
		self.glow_effect.setEnabled(True)

		self.clicked.connect(self._onClicked)

	def _boundPath(self) -> QPainterPath: 
		bound_path = QPainterPath()
		bound_path.addEllipse(0, 0, 500, 500)
		return bound_path

	def _filterPath(self) -> QPainterPath: 
		filter_path = QPainterPath()
		filter_path.moveTo(100, 150)
		filter_path.lineTo(400, 150)
		filter_path.lineTo(275, 250)
		filter_path.lineTo(275, 350)
		filter_path.lineTo(225, 400)
		filter_path.lineTo(225, 250)
		filter_path.closeSubpath()
		return filter_path

	def _filterPixmap(self, filter_color: str) -> QPixmap: 
		pixmap = QPixmap(500, 500)
		pixmap.fill(Qt.GlobalColor.transparent)
		painter = QPainter(pixmap)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(QBrush(QColor("#FFFFFF")))
		painter.drawPath(self._bound_path)
		painter.setBrush(QBrush(QColor(filter_color)))
		painter.drawPath(self._filter_path)
		painter.end()
		return pixmap

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

		pixmap = self._normal_pixmap if self._is_normal else self._abnormal_pixmap
		scaled_pixmap = pixmap.scaled(
			self.btn_size, self.btn_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
		)
		painter.drawPixmap(0, 0, scaled_pixmap)
		painter.end()

	def _onClicked(self) -> None: 
		current_option = self.filter_dialog.getCurrentFilterOptions()
		if self.filter_dialog.exec() == QDialog.DialogCode.Accepted:
			self.filter_option_changed.emit()
		else: 
			self.filter_dialog.setCurrentFilterOptions(current_option)

	def getCurrentFilterOptions(self) -> Tuple[SongType, Timeline]: 
		return self.filter_dialog.getCurrentFilterOptions()

	def setCurrentFilterOptions(self, option: Tuple[SongType, Timeline]) -> None: 
		self.filter_dialog.setCurrentFilterOptions(option)

	def getCurrentFilterOptionsDict(self) -> Dict[str, Any]: 
		song_type, timeline = self.getCurrentFilterOptions()
		return {
			"songs": song_type.value, 
			"timeline": Timeline.toStrList(timeline)
		}

	def setCurrentFilterOptionsDict(self, option: Dict[str, Any]) -> None: 
		song_type = SongType.fromStr(option["songs"])
		timeline = Timeline.fromStrList(option["timeline"])
		self.setCurrentFilterOptions((song_type, timeline))

	def setNormalState(self, search_content: str, filter_options: Tuple[SongType, Timeline]) -> None: 
		self._is_normal = (search_content == "") and (filter_options == (SongType.ALL, Timeline.PLAYABLE))
		self.update()


class FilterDialog(QDialog): 

	dialog_bonus = 1.2

	def __init__(self, btn_size: int, default_options: Dict[str, Any], parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		btn_size = int(btn_size * self.dialog_bonus)
		self.button_height = btn_size
		self.button_width = self.button_height * 3
		self.my_layout = QVBoxLayout(self)
		self.filter_columns = OptionButtonSetWidget(btn_size, 
			"楽曲", ["すべて", "書き下ろし楽曲", "APPENDあり"], default_options.get("songs", "すべて"), parent=self
		)
		self.timeline = OptionCheckBoxSetWidget(
			btn_size, "時間軸", ["サービス終了", "プレイ可能", "未公開"], default_options.get("timeline", ["プレイ可能"]), parent=self
		)
		self.my_layout.addWidget(self.filter_columns)
		self.my_layout.addWidget(self.timeline)

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

		self.my_layout.addWidget(self.button_widget)

		self.setModal(True)

	def getCurrentFilterOptions(self) -> Tuple[SongType, Timeline]: 
		return (
			SongType.fromStr(self.filter_columns.getCurrentOption()), 
			Timeline.fromStrList(self.timeline.getCurrentOptions())
		)

	def setCurrentFilterOptions(self, option: Tuple[SongType, Timeline]) -> None: 
		self.filter_columns.setCurrentOption(option[0].value)
		self.timeline.setCurrentOptions(Timeline.toStrList(option[1]))
