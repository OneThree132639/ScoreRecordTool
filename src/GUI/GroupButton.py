import logging
import numpy as np

from scipy.ndimage import binary_erosion
from typing import Callable, Dict, List, Optional, Tuple, Union

from PyQt5.QtCore import (
	pyqtBoundSignal, pyqtSignal, QMetaObject, QObject, QPoint, Qt, QRect, QRectF, QSize
)
from PyQt5.QtGui import (
	QBrush, QColor, QFont, QFontMetrics, QImage, QPainter, QPaintEvent, 
	QPalette, QPen, QPixmap, QTextDocument, 
	QTextOption
)
from PyQt5.QtWidgets import (
	QButtonGroup, QHBoxLayout, QListWidget, QListWidgetItem, 
	QPushButton, QSizePolicy, QVBoxLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from Basics.BasicClass import BasicButton
	from Basics.Enums.ButtonState import ButtonState
	from Basics.Enums.Group import Group
	from Basics.PyQt5Assistants.Drawer import drawRect
else: 
	from .Basics.BasicClass import BasicButton
	from .Basics.Enums.ButtonState import ButtonState
	from .Basics.Enums.Group import Group
	from .Basics.PyQt5Assistants.Drawer import drawRect

class GroupButton(BasicButton): 

	disabled_color = "#808080"

	size_changed = pyqtSignal()

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

	def updateSize(self, width: int, height: int) -> None: 
		self.setFixedSize(width, height)
		self.size_changed.emit()
		self.updateGeometry()

	def sizeHint(self) -> QSize: 
		return QSize(self.width(), self.height())

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
		self.updateSize(self.pic_size, self.pic_size)
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
	margin_percentage = 0.03
	leading_percentage = 0.00
	short_percentage = 0.20
	long_percentage = 0.15
	min_height_percentage = 0.4

	def __init__(self, group: Union[Group, str], icon_size: int, text: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(group, icon_size, parent)
		self.my_text = text
		self.icon_size = icon_size
		self.min_height = int(icon_size * self.min_height_percentage)
		self.margin = int(icon_size * self.margin_percentage)
		self.leading = int(icon_size * self.leading_percentage)
		self.short_size = int(icon_size * self.short_percentage)
		self.long_size = int(icon_size * self.long_percentage)

		self.updateSize(self.icon_size, self.min_height)

		self.document = QTextDocument()
		self.document.setDefaultTextOption(QTextOption(Qt.AlignmentFlag.AlignCenter))

	def getWrappedLines(self, doc: QTextDocument) -> List[str]: 
		lines = []
		block = doc.begin()
		while block.isValid(): 
			layout = block.layout()
			if layout is not None: 
				for i in range(layout.lineCount()): 
					line = layout.lineAt(i)
					start = line.textStart()
					end = start + line.textLength()
					lines.append(block.text()[start:end])
			block = block.next()
		return lines 

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
		rect = self.rect().adjusted(self.margin, self.margin, -self.margin, -self.margin)
		self.document.setTextWidth(rect.width())
		self.document.size()
		lines = self.getWrappedLines(self.document)
		font = QFont()
		font.setPixelSize(font_size)
		font.setFamily("FOT-RodinNTLG Pro")
		metrics = QFontMetrics(font)
		height = metrics.height()
		total_height = len(lines) * height + (len(lines) - 1) * self.leading + 2 * self.margin
		setting_height = max(total_height, self.min_height + 2 * self.margin)
		self.updateSize(self.icon_size, setting_height)
		start = (setting_height - total_height) / 2
		painter.setPen(QPen(color))
		painter.setFont(font)
		painter.setBrush(Qt.BrushStyle.NoBrush)
		for idx, line in enumerate(lines): 
			# line_width = metrics.boundingRect(line).width()
			line_width = metrics.horizontalAdvance(line)
			x = (rect.width() - line_width) / 2 + self.margin
			y = start + idx * (height + self.leading) + self.margin
			target_rect = QRectF(x, y, line_width, height)
			painter.drawText(target_rect, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, line)
		painter.end()

	def rename(self, new_text: str) -> None: 
		self.my_text = new_text
		self.my_group = new_text
		self.update()

class SafeSignalConnectionManager: 

	def __init__(self, sender: QWidget, signal: pyqtBoundSignal, slot: Callable, cleanup_callback: Optional[Callable]=None) -> None: 
		self.sender = sender
		self.signal = signal
		self.slot = slot
		self.connection = None
		self.cleanup_callback = cleanup_callback
		self._connected = False

		self.connect()

		def onDestroyed(): 
			self.disconnect()
			if self.cleanup_callback is not None: 
				self.cleanup_callback()

	def connect(self) -> None: 
		if not self._connected: 
			self.connection = self.signal.connect(self.slot)
			self._connected = True

	def disconnect(self) -> None: 
		if self._connected and self.connection is not None: 
			try: 
				self.signal.disconnect(self.slot)
			except Exception as e: 
				logging.warning("Failed to disconnect signal: %s", e)
			self._connected = False
			self.connection = None


class GroupButtonSet(QListWidget): 

	btn_spacing = 20
	num_default_btn = 8
	padding_percentage = 0.05
	unit_percentage = 0.7

	def __init__(self, 
			btn_size: int, group_masks: np.ndarray, 
			btn_config: Dict[str, Dict[str, str]], 
			checked_group: Union[int, str]=0, 
			custom_list: List[str]=[], 
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
		self.safe_connections: Dict[int, SafeSignalConnectionManager] = {}

		for btn_name in custom_list: 
			btn = TextButton(btn_name, btn_size, btn_name, self)
			self.button_list.append(btn)

		for btn in self.button_list:
			btn.setCheckable(True)
			btn.setEnabled(True)
			self.button_group.addButton(btn)

			item, container = self._createCenteredItem(btn)
			self.addItem(item)
			self.setItemWidget(item, container)

			self.safeConnect(btn, item)

			if btn.matchGroup(checked_group): 
				btn.setChecked(True)

		palette = self.palette()
		color = QColor("#5c5c7d")
		color.setAlpha(127)
		palette.setColor(QPalette.ColorRole.Base, color)
		self.setPalette(palette)
		self.setAutoFillBackground(True)

	def _isValid(self, object: Optional[Union[QWidget, QListWidgetItem]]) -> bool: 
		try: 
			return object is not None and hasattr(object, "isVisible")
		except: 
			return False

	def _cleanupButton(self, button: GroupButton) -> None: 
		button_id = id(button)
		if button_id in self.safe_connections: 
			del self.safe_connections[button_id]

	def safeConnect(self, button: GroupButton, item: QListWidgetItem) -> None: 
		def safeSlot(): 
			if not self._isValid(button) or not self._isValid(item): 
				return
			try: 
				self.updateItemSize(item, button)
			except RuntimeError as e: 
				logging.warning("Runtime Error occurred when updating item size: %s", e)

		connection = SafeSignalConnectionManager(
			button, button.size_changed, safeSlot, cleanup_callback=lambda: self._cleanupButton(button)
		)
		button_id = id(button)
		self.safe_connections[button_id] = connection


	def updateItemSize(self, item: QListWidgetItem, btn: GroupButton) -> None: 
		item.setSizeHint(btn.sizeHint())
		self.scheduleDelayedItemsLayout()

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

	def addButton(self, name: str) -> None: 
		btn = TextButton(name, self.btn_size, name, self)
		btn.setCheckable(True)
		btn.setEnabled(True)
		self.button_list.append(btn)
		self.button_group.addButton(btn)

		item, container = self._createCenteredItem(btn)
		self.addItem(item)
		self.setItemWidget(item, container)

		self.safeConnect(btn, item)

	def removeButton(self, name: str) -> None: 
		for i, btn in enumerate(self.button_list): 
			if isinstance(btn.my_group, str) and btn.my_group == name: 
				self.takeItem(i)
				self.button_group.removeButton(btn)
				self.button_list.pop(i)
				return

	def renameButton(self, old_name: str, new_name: str) -> None: 
		for btn in self.button_list: 
			if isinstance(btn.my_group, str) and btn.my_group == old_name: 
				btn: TextButton
				btn.rename(new_name)
				return

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

	def setCurrentGroup(self, group: Union[Group, str]) -> None: 
		for btn in self.button_list: 
			if isinstance(btn.my_group, Group) and isinstance(group, Group) and btn.my_group == group: 
				btn.setChecked(True)
				return
			elif isinstance(btn.my_group, str) and isinstance(group, str) and btn.my_group == group: 
				btn.setChecked(True)
				return

class AddGroupButton(QPushButton): 

	rounded_percentage = 0.05
	icon_percentage = 0.5
	border_percentage = 0.1
	stroke_percentage = 0.2

	def __init__(self, btn_size: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.btn_size = btn_size
		self.icon_size = int(btn_size * self.icon_percentage)
		self.setFixedSize(self.btn_size, self.btn_size)

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

		rounded_radius = int(self.btn_size * self.rounded_percentage)
		color = QColor(255, 255, 255, 255)
		border_color = QColor("#5c5c7d")
		pen = QPen()
		pen.setColor(border_color)
		pen.setWidth(int(self.btn_size * self.border_percentage))
		painter.setPen(pen)
		painter.setBrush(QBrush(color))
		painter.drawRoundedRect(self.rect(), rounded_radius, rounded_radius)

		painter.save()
		color = QColor(0, 0, 0, 255) if self.isEnabled() else QColor(128, 128, 128, 255)
		pen = QPen()
		pen.setColor(color)
		pen.setWidth(int(self.btn_size * self.stroke_percentage))
		painter.setPen(pen)
		painter.setBrush(Qt.BrushStyle.NoBrush)
		center = QPoint(self.width() // 2, self.height() // 2)
		side = self.icon_size // 2
		p11 = center + QPoint(-side, 0)
		p12 = center + QPoint(side, 0)
		painter.drawLine(p11, p12)
		p21 = center + QPoint(0, -side)
		p22 = center + QPoint(0, side)
		painter.drawLine(p21, p22)
		painter.restore()
		painter.end()

class SubGroupButton(QPushButton): 

	rounded_percentage = 0.05
	icon_percentage = 0.5
	border_percentage = 0.1
	stroke_percentage = 0.2

	def __init__(self, btn_size: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.btn_size = btn_size
		self.icon_size = int(btn_size * self.icon_percentage)
		self.setFixedSize(self.btn_size, self.btn_size)

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

		rounded_radius = int(self.btn_size * self.rounded_percentage)
		color = QColor(255, 255, 255, 255)
		border_color = QColor("#5c5c7d")
		pen = QPen()
		pen.setColor(border_color)
		pen.setWidth(int(self.btn_size * self.border_percentage))
		painter.setPen(pen)
		painter.setBrush(QBrush(color))
		painter.drawRoundedRect(self.rect(), rounded_radius, rounded_radius)

		painter.save()
		color = QColor(0, 0, 0, 255) if self.isEnabled() else QColor(128, 128, 128, 255)
		pen = QPen()
		pen.setColor(color)
		pen.setWidth(int(self.btn_size * self.stroke_percentage))
		painter.setPen(pen)
		painter.setBrush(Qt.BrushStyle.NoBrush)
		center = QPoint(self.width() // 2, self.height() // 2)
		side = self.icon_size // 2
		p11 = center + QPoint(-side, 0)
		p12 = center + QPoint(side, 0)
		painter.drawLine(p11, p12)
		painter.restore()
		painter.end()

class SettingGroupButton(QPushButton): 

	rounded_percentage = 0.05
	icon_percentage = 0.8
	border_percentage = 0.1
	stroke_percentage = 0.1

	def __init__(self, btn_size: int, icon_array: np.ndarray, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.btn_size = btn_size
		self.icon_size = int(btn_size * self.icon_percentage)
		self.setFixedSize(self.btn_size, self.btn_size)
		self.my_mask = icon_array
		self.enabled_pixmap = self._generatePixmap(QColor(0, 0, 0, 255))
		self.disabled_pixmap = self._generatePixmap(QColor(128, 128, 128, 255))

	def _generatePixmap(self, color: QColor) -> QPixmap: 
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

		pixmap = pixmap.scaled(self.icon_size, self.icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

		return pixmap

	def paintEvent(self, event: QPaintEvent) -> None: 
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

		rounded_radius = int(self.btn_size * self.rounded_percentage)
		color = QColor(255, 255, 255, 255)
		border_color = QColor("#5c5c7d")
		pen = QPen()
		pen.setColor(border_color)
		pen.setWidth(int(self.btn_size * self.border_percentage))
		painter.setPen(pen)
		painter.setBrush(QBrush(color))
		painter.drawRoundedRect(self.rect(), rounded_radius, rounded_radius)

		painter.save()
		target_rect = QRectF(
			(self.width() - self.icon_size) / 2, (self.height() - self.icon_size) / 2, 
			self.icon_size, self.icon_size
		)
		painter.drawPixmap(
			target_rect.topLeft(), 
			self.enabled_pixmap if self.isEnabled() else self.disabled_pixmap, 
		)
		painter.restore()
		painter.end()

class GroupButtonWidget(QWidget): 

	button_size_percentage = 0.30
	manage_height_percentage = 0.50
	padding_percentage = 0.05

	def __init__(self, 
			btn_size: int, group_masks: np.ndarray, setting_mask: np.ndarray, 
			btn_config: Dict[str, Dict[str, str]], checked_group: Union[int, str]=0, 
			custom_list: List[str]=[], 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.group_button_set = GroupButtonSet(
			btn_size, group_masks, btn_config, checked_group, 
			custom_list=custom_list, 
			parent=self
		)

		self.manage_widget = QWidget(self) 
		self.manage_layout = QHBoxLayout(self.manage_widget)
		self.add_button = AddGroupButton(int(btn_size * self.button_size_percentage), self.manage_widget)
		self.sub_button = SubGroupButton(int(btn_size * self.button_size_percentage), self.manage_widget)
		self.setting_button = SettingGroupButton(int(btn_size * self.button_size_percentage), setting_mask, self.manage_widget)
		self.manage_widget.setFixedHeight(int(btn_size * self.manage_height_percentage))
		self.manage_widget.setLayout(self.manage_layout)
		self.manage_layout.addStretch()
		self.manage_layout.addWidget(self.add_button)
		self.manage_layout.addStretch()
		self.manage_layout.addWidget(self.sub_button)
		self.manage_layout.addStretch()
		self.manage_layout.addWidget(self.setting_button)
		self.manage_layout.addStretch()
		self.manage_layout.setSpacing(1)
		self.manage_layout.setContentsMargins(0, 0, 0, 0)
		self.manage_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

		self.my_layout = QVBoxLayout(self)
		self.setLayout(self.my_layout)
		self.my_layout.addWidget(self.group_button_set, Qt.AlignmentFlag.AlignHCenter)
		self.my_layout.addWidget(self.manage_widget, Qt.AlignmentFlag.AlignHCenter)
		self.my_layout.setContentsMargins(0, 0, 0, 0)

		padding = int(btn_size * self.padding_percentage)
		self.setFixedWidth(btn_size + 2 * padding)

		self.group_button_set.button_group.buttonClicked.connect(self._onGroupButtonClicked) 
		self.setting_button.clicked.connect(lambda: logging.debug("setting button clicked. "))

		self._onGroupButtonClicked()

	def _onGroupButtonClicked(self) -> None: 
		current_group = self.group_button_set.getCurrentGroup()
		if isinstance(current_group, Group): 
			self.sub_button.setEnabled(False)
			self.setting_button.setEnabled(False)
		elif isinstance(current_group, str): 
			self.sub_button.setEnabled(True)
			self.setting_button.setEnabled(True)

	def getCurrentGroup(self) -> Union[Group, str]: 
		return self.group_button_set.getCurrentGroup()

	def getCurrentGroupConfig(self) -> Union[int, str]: 
		return self.group_button_set.getCurrentGroupConfig()

	def addButton(self, group_name: str) -> None: 
		self.group_button_set.addButton(group_name)

	def removeButton(self, group_name: str) -> None: 
		self.group_button_set.removeButton(group_name)