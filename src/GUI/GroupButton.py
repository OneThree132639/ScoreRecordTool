import numpy as np

from scipy.ndimage import binary_erosion
from typing import Dict, List, Optional, Tuple, Union

from PyQt5.QtCore import (
	Qt, QSize
)
from PyQt5.QtGui import (
	QColor, QImage, QPainter, QPaintEvent, 
	QPalette, QPen, QPixmap, QResizeEvent, QTextDocument, 
	QTextOption
)
from PyQt5.QtWidgets import (
	QButtonGroup, QHBoxLayout, QListWidget, QListWidgetItem, 
	QWidget
)

if __package__ is None or __package__ == "": 
	from Basics.BasicClass import BasicButton
	from Basics.Enums.ButtonState import ButtonState
	from Basics.Enums.Group import Group
else: 
	from .Basics.BasicClass import BasicButton
	from .Basics.Enums.ButtonState import ButtonState
	from .Basics.Enums.Group import Group

class GroupButton(BasicButton): 

	disabled_color = "#808080"

	def __init__(self, group: Union[Group, str], icon_size: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.my_group = group
		self.icon_size = icon_size

		self.setStyleSheet((
			"QPushButton {"
			"\tborder: 0px; "
			"\toutline: none; "
			"}"
		))

	def matchGroup(self, value: Union[int, str]) -> bool: 
		if isinstance(self.my_group, Group) and isinstance(value, int): 
			return self.my_group.value == value
		elif isinstance(self.my_group, str) and isinstance(value, str): 
			return self.my_group == value
		return False

class UnitButton(GroupButton): 

	unchecked_color = "#FFFFFF"
	border_color = "#A9A9BD"
	border_radius_percentage = 0.1
	pic_size_percentage = 0.6

	def __init__(self, group: Union[Group, str], icon_size: int, mask: np.ndarray, checked_color: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(group, icon_size, parent)
		self.pic_size = int(icon_size * self.pic_size_percentage)
		self.my_mask = mask
		self.checked_color = checked_color
		self.setFixedSize(self.pic_size, self.pic_size)
		self.updateState()

	def _drawBorderOnPixmap(self, pixmap: QPixmap, border_width: int) -> QPixmap: 
		eroded = binary_erosion(self.my_mask, structure=np.ones((3, 3)))
		border = self.my_mask & ~eroded

		result = QPixmap(pixmap.size())
		result.fill(Qt.GlobalColor.transparent)
		painter = QPainter(result)
		painter.setPen(QPen(QColor(self.border_color), border_width))
		painter.setBrush(Qt.BrushStyle.NoBrush)

		border_coords = np.where(border)
		for y, x in zip(border_coords[0], border_coords[1]): 
			painter.drawPoint(x, y)

		painter.drawPixmap(0, 0, pixmap)

		painter.end()
		return result

	def _generatePixmap(self, color: QColor, border_width: int) -> QPixmap: 
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

		if border_width > 0: 
			pixmap = self._drawBorderOnPixmap(pixmap, border_width)

		return pixmap

	def _getCurrentIconInfos(self) -> Tuple[QColor, int]: 
		border_width = int(self.pic_size * self.border_radius_percentage)
		if self._current_state == ButtonState.DISABLED: 
			return QColor(self.disabled_color), border_width
		elif self._current_state == ButtonState.NORMAL: 
			return QColor(self.unchecked_color), 0
		else: 
			return QColor(self.checked_color), border_width

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		color, border_width = self._getCurrentIconInfos()
		pixmap = self._generatePixmap(color, border_width)
		scaled_pixmap = pixmap.scaled(self.pic_size, self.pic_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
		x = (self.width() - scaled_pixmap.width()) // 2
		y = (self.height() - scaled_pixmap.height()) // 2
		painter.drawPixmap(x, y, scaled_pixmap)
		painter.end()

class TextButton(GroupButton): 

	unchecked_color = "#FFFFFF"
	checked_color = "#A1F4EB"
	padding_percentage = 0.03
	short_percentage = 0.20
	long_percentage = 0.10
	min_height_percentage = 0.7

	def __init__(self, group: Union[Group, str], icon_size: int, text: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(group, icon_size, parent)
		self.my_text = text
		self.min_height = int(icon_size * self.min_height_percentage)
		self.short_size = int(icon_size * self.short_percentage)
		self.long_size = int(icon_size * self.long_percentage)

		self.setFixedWidth(self.icon_size)

		self.document = QTextDocument()
		self.document.setDefaultTextOption(QTextOption(Qt.AlignmentFlag.AlignCenter))

	def updateDocument(self) -> None: 
		padding = int(self.icon_size * self.padding_percentage)
		available_width = self.width() - 2 * padding

		font_size = self.short_size if len(self.my_text) <= 3 else self.long_size
		html_text = (
			"<span style=\"font-size: {}px; font-family: FOT-RodinNTLG Pro; \">{}</span>"
		).format(font_size, self.my_text)
		self.document.setHtml(html_text)
		self.document.setTextWidth(available_width)

		doc_height = self.document.size().height()
		self.setFixedHeight(min(int(doc_height), self.min_height) + 2 * padding)
		self.update()

	def setText(self, text: str) -> None: 
		super().setText("")
		self.my_text = text
		self.updateDocument()

	def resizeEvent(self, event: QResizeEvent) -> None: 
		super().resizeEvent(event)
		self.updateDocument()

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		if self._current_state == ButtonState.DISABLED: 
			color = QColor(self.disabled_color)
		elif self._current_state == ButtonState.NORMAL: 
			color = QColor(self.unchecked_color)
		else: 
			color = QColor(self.checked_color)

		font_size = self.short_size if len(self.my_text) <= 3 else self.long_size

		html_text = (
			"<span style=\"color: {}; font-size: {}px; font-family: FOT-RodinNTLG Pro; \">{}</span>"
		).format(color.name(), font_size, self.my_text)

		self.document.setHtml(html_text)
		padding = int(self.icon_size * self.padding_percentage)
		rect = self.rect().adjusted(padding, padding, -padding, -padding)
		self.document.setTextWidth(rect.width())
		painter.translate(rect.topLeft())
		self.document.drawContents(painter)
		painter.end()


class GroupButtonSet(QListWidget): 

	btn_spacing = 20
	num_default_btn = 8
	padding_percentage = 0.05
	unit_percentage = 0.7

	def __init__(self, 
			btn_size: int, group_masks: np.ndarray, 
			btn_config: Dict[str, Dict[str, str]], 
			checked_group: Union[int, str]=0, 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.btn_size = btn_size
		padding = int(self.btn_size * self.padding_percentage)
		unit_size = int(self.btn_size * self.unit_percentage)
		self.btn_config = btn_config
		self.group_masks = group_masks

		self.setFlow(QListWidget.Flow.TopToBottom)
		self.setSelectionMode(QListWidget.SelectionMode.NoSelection)
		self.setUniformItemSizes(False)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
		self.setFixedWidth(self.btn_size + 2 * padding)

		self.all_button = TextButton(Group.ALL, btn_size, "すべて", self)
		self.vs_button = UnitButton(Group.VS, unit_size, group_masks[Group.VS.value - 1], btn_config["vs"]["color"], self)
		self.ln_button = UnitButton(Group.LN, unit_size, group_masks[Group.LN.value - 1], btn_config["ln"]["color"], self)
		self.mmj_button = UnitButton(Group.MMJ, unit_size, group_masks[Group.MMJ.value - 1], btn_config["mmj"]["color"], self)
		self.vbs_button = UnitButton(Group.VBS, unit_size, group_masks[Group.VBS.value - 1], btn_config["vbs"]["color"], self)
		self.ws_button = UnitButton(Group.WS, unit_size, group_masks[Group.WS.value - 1], btn_config["ws"]["color"], self)
		self.ng_button = UnitButton(Group.NG, unit_size, group_masks[Group.NG.value - 1], btn_config["ng"]["color"], self)
		self.other_button = TextButton(Group.OTHER, btn_size, "その他", self)

		self.button_group = QButtonGroup(self)
		self.button_group.setExclusive(True)

		self.button_list: List[GroupButton] = [
			self.all_button,
			self.vs_button, self.ln_button, self.mmj_button, 
			self.vbs_button, self.ws_button, self.ng_button,
			self.other_button
		]

		for btn in self.button_list:
			btn.setCheckable(True)
			btn.setEnabled(True)
			self.button_group.addButton(btn)

			item, container = self._createCenteredItem(btn)
			self.addItem(item)
			self.setItemWidget(item, container)

			if btn.matchGroup(checked_group): 
				btn.setChecked(True)

		palette = self.palette()
		color = QColor("#5c5c7d")
		color.setAlpha(127)
		palette.setColor(QPalette.ColorRole.Base, color)
		self.setPalette(palette)
		self.setAutoFillBackground(True)

	def _createCenteredItem(self, button: BasicButton) -> Tuple[QListWidgetItem, QWidget]: 
		container = QWidget(self)
		layout = QHBoxLayout(container)
		layout.addStretch()
		layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
		layout.addStretch()
		layout.setContentsMargins(0, 0, 0, 0)
		container.setLayout(layout)

		item = QListWidgetItem(self)
		size_hint = QSize(button.width(), button.height() + self.btn_spacing)
		item.setSizeHint(size_hint)
		return item, container

	def addButton(self, button: BasicButton) -> None: 
		button.setCheckable(True)
		button.setEnabled(True)
		self.button_list.append(button)
		self.button_group.addButton(button)

		item, container = self._createCenteredItem(button)
		self.addItem(item)
		self.setItemWidget(item, container)

	def getCurrentGroup(self) -> Union[Group, str]: 
		for btn in self.button_list: 
			if btn.isChecked(): 
				return btn.my_group
		return Group.ALL

	def getCurrentGroupConfig(self) -> Union[int, str]: 
		group = self.getCurrentGroup()
		if isinstance(group, Group): 
			return group.value
		elif isinstance(group, str): 
			return group
		return group

	def setCurrentGroupConfig(self, value: Union[int, str]) -> None: 
		for btn in self.button_list: 
			if isinstance(btn.my_group, Group) and btn.my_group.value == value: 
				btn.setChecked(True)
				return
			elif isinstance(btn.my_group, str) and btn.my_group == value: 
				btn.setChecked(True)
				return