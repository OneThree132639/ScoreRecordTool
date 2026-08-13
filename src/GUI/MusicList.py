import logging
import numpy as np
import pandas as pd

from typing import Any, Callable, Dict, Literal, Optional, Tuple, Union
from typing import overload

from PyQt5.QtCore import (
	pyqtSignal, QEasingCurve, QPropertyAnimation, Qt, QSize, QTimer
)
from PyQt5.QtGui import (
	QFont, QImage, QPixmap, QResizeEvent
)
from PyQt5.QtWidgets import (
	QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QScrollBar, 
	QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from Basics.Enums.Difficulty import Difficulty
	from Basics.Enums.Group import Group
	from Basics.Enums.FilterOptions import SongType
	from Basics.Enums.SortType import SortType
	from Basics.MusicInfo import MarqueeLabel, OrdinaryLabel, AppendLabel
else: 
	from .Basics.Enums.Difficulty import Difficulty
	from .Basics.Enums.Group import Group
	from .Basics.Enums.FilterOptions import SongType
	from .Basics.Enums.SortType import SortType
	from .Basics.MusicInfo import MarqueeLabel, OrdinaryLabel, AppendLabel

class BasicCard(QWidget): 

	my_layout_spacing = 5

	@overload
	def __init__(self, 
			small_height: int, large_height: int, icon_size: int, label_size: int, 
			music_id: int, title: str, difficulty: Difficulty, level: int, 
			cover: Literal[None], pixmap: Literal[None], parent: Optional[QWidget]=None
		) -> None: ...

	@overload
	def __init__(self, 
			small_height: int, large_height: int, icon_size: int, label_size: int, 
			music_id: int, title: str, difficulty: Difficulty, level: int, 
			cover: np.ndarray, pixmap: Literal[None], parent: Optional[QWidget]=None
		) -> None: ...

	@overload
	def __init__(self, 
			small_height: int, large_height: int, icon_size: int, label_size: int, 
			music_id: int, title: str, difficulty: Difficulty, level: int, 
			cover: QPixmap, pixmap: QPixmap, parent: Optional[QWidget]=None
		) -> None: ...

	def __init__(self, 
			small_height: int, large_height: int, icon_size: int, label_size: int, 
			music_id: int, title: str, difficulty: Difficulty, level: int, 
			cover: Optional[Union[np.ndarray, QPixmap]], 
			pixmap: Optional[QPixmap], 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.small_height = small_height
		self.large_height = large_height
		self.icon_size = icon_size
		self.label_size = label_size

		self.music_id = int(music_id)
		self.title = title
		self.difficulty = difficulty
		self.level = level
		self.cover = cover
		self.pixmap: Optional[QPixmap] = None
		self.scaled_pixmap: Optional[QPixmap] = None

		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

		self.cover_label = QLabel(self)
		self.cover_label.setFixedSize(self.icon_size, self.icon_size)
		self.cover_label.setScaledContents(True)
		if self.cover is None: 
			self.cover_label.setText("ジャケット画像がありません")
			font = QFont()
			font.setPixelSize(self.small_height)
			self.cover_label.setFont(font)
		elif isinstance(self.cover, np.ndarray): 
			self.pixmap = self._np_to_pixmap(self.cover)
			self.scaled_pixmap = self.pixmap.scaled(self.cover_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
			self.cover_label.setPixmap(self.scaled_pixmap)
		elif isinstance(self.cover, QPixmap): 
			self.cover_label.setPixmap(self.cover)
			self.pixmap = pixmap
			self.scaled_pixmap = cover

		self.info_widget = QWidget(self)
		self.info_layout = QVBoxLayout(self.info_widget)
		self.info_widget.setLayout(self.info_layout)

		self.my_layout = QHBoxLayout(self)
		self.my_layout.setSpacing(self.my_layout_spacing)
		self.setLayout(self.my_layout)

	def _np_to_pixmap(self, image: np.ndarray) -> QPixmap: 
		if image.dtype != np.uint8: 
			image = image.astype(np.uint8)
		image = np.ascontiguousarray(image)
		shape: Tuple[int, int, int] = image.shape
		height, width, channels = shape
		bytes_per_line = channels * width
		qimage = QImage(image.copy().data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888) # type: ignore
		return QPixmap.fromImage(qimage)

	def getData(self) -> Any: 
		raise NotImplementedError("Subclasses should implement this method. ")
	
class NormalCard(BasicCard): 

	@overload
	def __init__(self, 
			small_height: int, large_height: int, icon_size: int, label_size: int, 
			music_id: int, title: str, difficulty: Difficulty, level: int, config: Dict[str, str], 
			cover: Literal[None], pixmap: Literal[None], parent: Optional[QWidget]=None
		) -> None: ...

	@overload
	def __init__(self, 
			small_height: int, large_height: int, icon_size: int, label_size: int, 
			music_id: int, title: str, difficulty: Difficulty, level: int, config: Dict[str, str], 
			cover: np.ndarray, pixmap: Literal[None], parent: Optional[QWidget]=None
		) -> None: ...

	@overload
	def __init__(self, 
			small_height: int, large_height: int, icon_size: int, label_size: int, 
			music_id: int, title: str, difficulty: Difficulty, level: int, config: Dict[str, str], 
			cover: QPixmap, pixmap: QPixmap, parent: Optional[QWidget]=None
		) -> None: ...

	def __init__(self, 
			small_height: int, large_height: int, icon_size: int, label_size: int, 
			music_id: int, title: str, difficulty: Difficulty, level: int, 
			config: Dict[str, str], cover: Optional[Union[np.ndarray, QPixmap]], 
			pixmap: Optional[QPixmap], 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(
			small_height, large_height, icon_size, label_size, 
			music_id, title, difficulty, level, cover, pixmap, parent
		)
		self.config = config

		if difficulty == Difficulty.APPEND: 
			self.level_label = AppendLabel(level, False, self.label_size, difficulty, config, self)
		else: 
			self.level_label = OrdinaryLabel(level, False, self.label_size, difficulty, config, self)

		self.title_label = MarqueeLabel(title, "nintendo_NTLG-DB_001", self.small_height, False)
		self.info_layout.addWidget(self.title_label)

		self.my_layout.addWidget(self.level_label)
		self.my_layout.addWidget(self.cover_label)
		self.my_layout.addWidget(self.info_widget)

	def getData(self) -> Tuple[int, str, Difficulty, int, Dict[str, str], Optional[QPixmap], Optional[QPixmap]]: 
		pixmap = None if self.pixmap is None else self.pixmap.copy()
		scaled_pixmap = None if self.scaled_pixmap is None else self.scaled_pixmap.copy()
		return (
			self.music_id, self.title, self.difficulty, self.level, 
			self.config, scaled_pixmap, pixmap
		)

	def pause(self) -> None: 
		self.title_label.pause()

	def resume(self) -> None: 
		self.title_label.resume()

class MusicCard(BasicCard): 

	def __init__(self, 
		small_height: int, large_height: int, icon_size: int, label_size: int, 
		music_id: int, title: str, composer: str, vocal: str, 
		difficulty: Difficulty, level: int, config: Dict[str, Any], 
		cover: Optional[Union[np.ndarray, QPixmap]], pixmap: Optional[QPixmap], 
		parent: Optional[QWidget]=None
	) -> None: 
		super().__init__(small_height, large_height, icon_size, label_size, 
			music_id, title, difficulty, level, cover, pixmap, parent
		)
		self.composer = composer
		self.vocal = vocal
		self.config = config

		if difficulty == Difficulty.APPEND: 
			self.level_label = AppendLabel(level, True, self.label_size, difficulty, config, self)
		else: 
			self.level_label = OrdinaryLabel(level, True, self.label_size, difficulty, config, self)

		self.title_label = MarqueeLabel(title, "FOT-RodinNTLG Pro", self.large_height, False)
		self.composer_label = MarqueeLabel(composer, "nintendo_NTLG-DB_001", self.small_height, False)
		self.vocal_label = MarqueeLabel(vocal, "nintendo_NTLG-DB_001", self.small_height, False)
		self.info_layout.addWidget(self.title_label)
		self.info_layout.addWidget(self.composer_label)
		self.info_layout.addWidget(self.vocal_label)

		self.my_layout.addWidget(self.level_label)
		self.my_layout.addWidget(self.cover_label)
		self.my_layout.addWidget(self.info_widget)

	def getData(self) -> Tuple[int, str, str, str, Difficulty, int, Dict[str, Any], Optional[QPixmap], Optional[QPixmap]]: 
		pixmap = None if self.pixmap is None else self.pixmap.copy()
		scaled_pixmap = None if self.scaled_pixmap is None else self.scaled_pixmap.copy()
		return (self.music_id, self.title, self.composer, self.vocal, 
			self.difficulty, self.level, self.config, scaled_pixmap, pixmap
		)

	def pause(self) -> None: 
		self.title_label.pause()
		self.composer_label.pause()
		self.vocal_label.pause()

	def resume(self) -> None: 
		self.title_label.resume()
		self.composer_label.resume()
		self.vocal_label.resume()

class EmptyLabel(QLabel): 

	def __init__(self, pixel_size: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.setText("該当する楽曲がありません")
		self.setWordWrap(False)

		self.setStyleSheet(
			"QLabel {"
			"	color: #000000; "
			"	background-color: transparent; "
			"}"
		)

		font = QFont()
		font.setPixelSize(pixel_size)
		self.setFont(font)

class DisplayCard(QWidget): 

	padding = 25
	my_layout_spacing = 10
	cover_text_spacing = 20
	size_percentage = 0.35

	def __init__(self, 
			small_height: int, large_height: int, init_height: int, 
			title: str, composer: str, vocal: str, 
			pixmap: Optional[QPixmap], parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.small_height = small_height
		self.large_height = large_height
		self.icon_size = int(init_height * self.size_percentage)

		self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
		self.setFixedWidth(self.icon_size + 2 * self.padding)
		self.my_layout = QVBoxLayout()
		self.my_layout.setSpacing(self.my_layout_spacing)
		self.setLayout(self.my_layout)

		self.title_label = MarqueeLabel(title, "FOT-RodinNTLG Pro", self.large_height, False)
		self.composer_label = MarqueeLabel(composer, "nintendo_NTLG-DB_001", self.small_height, False)
		self.vocal_label = MarqueeLabel(vocal, "nintendo_NTLG-DB_001", self.small_height, True)

		self.cover_label = QLabel(self)
		self.cover_label.setFixedSize(self.icon_size, self.icon_size)
		self.cover_label.setScaledContents(True)
		if pixmap is None: 
			self.cover_label.setText("ジャケット画像がありません")
			font = QFont()
			font.setPixelSize(self.large_height)
			self.cover_label.setFont(font)
		elif isinstance(pixmap, QPixmap): 
			self.cover_label.setPixmap(pixmap)

		self.my_layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignCenter)
		self.my_layout.addSpacing(self.cover_text_spacing)
		self.my_layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignLeft)
		self.my_layout.addWidget(self.composer_label, alignment=Qt.AlignmentFlag.AlignLeft)
		self.my_layout.addWidget(self.vocal_label, alignment=Qt.AlignmentFlag.AlignLeft)

	def updateData(self, title: str, composer: str, vocal: str, 
			pixmap: Optional[QPixmap]
		) -> None: 
		self.title_label.setText(title)
		self.composer_label.setText(composer)
		self.vocal_label.setText(vocal)

		self.cover_label.clear()
		if pixmap is None: 
			self.cover_label.setText("ジャケット画像がありません")
			font = QFont()
			font.setPixelSize(self.large_height)
			self.cover_label.setFont(font)
		elif isinstance(pixmap, QPixmap): 
			self.cover_label.setPixmap(pixmap)

	def pause(self) -> None: 
		self.title_label.pause()
		self.composer_label.pause()
		self.vocal_label.pause()

	def resume(self) -> None: 
		self.title_label.resume()
		self.composer_label.resume()
		self.vocal_label.resume()

class AnimationScrolling(QWidget): 

	animation_duration = 500

	animation_value_changed = pyqtSignal(int)

	def __init__(self, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)

		self._animation = QPropertyAnimation()
		self._animation_scrollbar = QScrollBar()
		self._animation_scrollbar.hide()
		self._animation.setTargetObject(self._animation_scrollbar)
		self._animation.setPropertyName(b"value")
		self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
		self._animation.setDuration(self.animation_duration)
		self._animation_dominant = False

		self._animation_scrollbar.valueChanged.connect(self._onAnimationValueChanged)
		self._animation.finished.connect(self._onAnimationStopped)

	def _onAnimationValueChanged(self, value: int) -> None: 
		if self._animation_dominant: 
			self.animation_value_changed.emit(value)

	def _onAnimationStopped(self) -> None: 
		self._animation_dominant = False

	def startAnimation(self, start_value: int, end_value: int) -> None: 
		self._animation_scrollbar.setRange(start_value, end_value)
		self._animation.setStartValue(start_value)
		self._animation.setEndValue(end_value)
		self._animation_dominant = True
		self._animation.start()


class MusicList(QListWidget): 

	stop_interval = 100
	update_interval = 50
	animation_duration = 500

	music_selected = pyqtSignal(int)

	def __init__(self, pixel_size: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)

		self.setFlow(QListWidget.Flow.TopToBottom)
		self.setSelectionMode(QListWidget.SelectionMode.NoSelection)
		self.setUniformItemSizes(False)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)

		self.music_list = pd.DataFrame()
		self._current_index = 0
		self._num_line = 0
		self._num_pad = 0
		self.normal_height: Optional[int] = None
		self.music_height: Optional[int] = None

		self._program_update = False
		self._is_scrolling = False

		self._stop_timer = QTimer(self)
		self._stop_timer.setInterval(self.stop_interval)
		self._stop_timer.timeout.connect(self._onScrollStop)

		self._update_timer = QTimer(self)
		self._update_timer.setSingleShot(True)
		self._update_timer.setInterval(self.update_interval)
		self._update_timer.timeout.connect(self._updateAllContainerWidths)

		self.empty_label = EmptyLabel(pixel_size, self)
		self.empty_label.raise_()
		
		vertical_scrollbar = self.verticalScrollBar()
		assert vertical_scrollbar is not None
		vertical_scrollbar.valueChanged.connect(self._onScrollBarValueChanged)

		self._animation_scrolling = AnimationScrolling(self)
		self._animation_scrolling.animation_value_changed.connect(self._onAnimationValueChanged)

		QTimer.singleShot(0, self._setEmptyLabelPosition)

	def _setEmptyLabelPosition(self) -> None: 
		rect = self.rect()
		label_size = self.empty_label.sizeHint()
		x = (rect.width() - label_size.width()) // 2
		y = (rect.height() - label_size.height()) // 2
		self.empty_label.setGeometry(x, y, label_size.width(), label_size.height())

	def _getAvailableWidth(self) -> int: 
		viewport = self.viewport()
		assert viewport is not None
		vertical_scrollbar = self.verticalScrollBar()
		assert vertical_scrollbar is not None

		viewport_width = viewport.width()
		scroll_bar_width = vertical_scrollbar.width() if vertical_scrollbar.isVisible() else 0

		return viewport_width - scroll_bar_width - self.viewportMargins().left() - self.viewportMargins().right()

	def _addContainer(self, row: pd.Series, vocal_table: pd.DataFrame, 
			difficulty: Difficulty, config: Dict[str, Any], 
			get_cover_func: Callable[[int], Optional[np.ndarray]], 
			create_container: Callable[
				[
					pd.Series, pd.DataFrame, Difficulty, Dict[str, Any], Callable[[int], 
					Optional[np.ndarray]], Optional[int], Optional[int]
				], 
				Tuple[QStackedWidget, int, int]
			]
		) -> None: 
		self._program_update = True
		container, self.normal_height, self.music_height = create_container(
			row, vocal_table, difficulty, config, get_cover_func, self.normal_height, self.music_height
		)
		item = QListWidgetItem()
		item.setSizeHint(QSize(0, container.sizeHint().height()))
		self.addItem(item)
		self.setItemWidget(item, container)
		self._program_update = False

	def _insertContainer(self, row: pd.Series, vocal_table: pd.DataFrame, 
			difficulty: Difficulty, config: Dict[str, Any], 
			index: int, get_cover_func: Callable[[int], Optional[np.ndarray]], 
			create_container: Callable[
				[
					pd.Series, pd.DataFrame, Difficulty, Dict[str, Any], Callable[[int], 
					Optional[np.ndarray]], Optional[int], Optional[int]
				], 
				Tuple[QStackedWidget, int, int]
			]
		) -> None: 
		self._program_update = True
		container, self.normal_height, self.music_height = create_container(
			row, vocal_table, difficulty, config, get_cover_func, self.normal_height, self.music_height
		)
		item = QListWidgetItem()
		item.setSizeHint(QSize(0, container.sizeHint().height()))
		self.insertItem(index, item)
		self.setItemWidget(item, container)
		self._program_update = False

	def refreshData(self, 
			music_table: Optional[pd.DataFrame], 
			vocal_table: Optional[pd.DataFrame], 
			difficulty: Difficulty, config: Dict[str, Any], 
			get_cover_func: Callable[[int], Optional[np.ndarray]], 
			create_container: Callable[
				[
					pd.Series, pd.DataFrame, Difficulty, Dict[str, Any], Callable[[int], 
					Optional[np.ndarray]], Optional[int], Optional[int]
				], 
				Tuple[QStackedWidget, int, int]
			]
		) -> None: 
		if music_table is None or vocal_table is None: 
			logging.warning("Music table or vocal table is None, cannot refresh data.")
			return
		self.empty_label.hide()
		self.setUpdatesEnabled(False)
		self._num_line = len(music_table)
		self._addContainer(music_table.iloc[self._num_line - 1], 
			vocal_table, difficulty, config, get_cover_func=get_cover_func, 
			create_container=create_container
		)
		viewport_height = self._getViewportHeight()
		assert self.normal_height is not None
		self._num_pad = int((viewport_height - self.normal_height) / (2 * self.normal_height)) + 4
		for i in range(self._num_pad - 1): 
			self._insertContainer(
				music_table.iloc[(self._num_line - 2 - i) % self._num_line], 
				vocal_table, difficulty, config, index=0, get_cover_func=get_cover_func, 
				create_container=create_container
			)
		for _, (_, row) in enumerate(music_table.iterrows()): 
			self._addContainer(
				row, vocal_table, difficulty, config, get_cover_func=get_cover_func, 
				create_container=create_container
			)
		for i in range(self._num_pad): 
			self._addContainer(
				music_table.iloc[i % self._num_line], 
				vocal_table, difficulty, config, get_cover_func=get_cover_func, 
				create_container=create_container
			)
		self.music_list = music_table.reset_index(drop=True)
		self._updateAllContainerWidths()
		self.setUpdatesEnabled(True)
		self._setVerticalScrollBarValue(self._getTargetScrollValue(self._current_index))
		self._updateAllWidgets(is_special=True, special_index=self._current_index + self._num_pad)

	def _updateAllWidgets(self, is_special: bool, special_index: int = 0) -> None: 
		assert self.normal_height is not None
		assert self.music_height is not None
		self.setUpdatesEnabled(False)

		for i in range(self.count()): 
			item = self.item(i)
			assert item is not None
			container: QStackedWidget = self.itemWidget(item) 
			assert container is not None
			if is_special and i == special_index: 
				container.setCurrentIndex(1)
				container.adjustSize()
				size_hint = item.sizeHint()
				item.setSizeHint(QSize(size_hint.width(), self.music_height))
				music_card: MusicCard = container.widget(1)
				assert music_card is not None
				music_card.resume()
			else: 
				container.setCurrentIndex(0)
				container.adjustSize()
				size_hint = item.sizeHint()
				item.setSizeHint(QSize(size_hint.width(), self.normal_height))
				music_card: MusicCard = container.widget(1)
				assert music_card is not None
				music_card.pause()

		self.setUpdatesEnabled(True)
		viewport = self.viewport()
		assert viewport is not None
		viewport.update()

	def _getCurrentIndex(self) -> int: 
		if self.normal_height is None: 
			return 0
		scroll_value = self._getCurrentValue()
		list_index = int((scroll_value + self._getViewportHeight() / 2) / self.normal_height)
		return (list_index - self._num_pad) % self._num_line

	def _getCurrentValue(self) -> int: 
		vertical_scrollbar = self.verticalScrollBar()
		assert vertical_scrollbar is not None
		return vertical_scrollbar.value()

	def _getViewportHeight(self) -> int: 
		viewport = self.viewport()
		assert viewport is not None
		return viewport.height()

	def _getTargetScrollValue(self, index: int) -> int: 
		assert self.normal_height is not None
		assert self.music_height is not None
		middle_value = (index + self._num_pad) * self.normal_height + 0.5 * self.music_height
		viewport_height = self._getViewportHeight()
		target_value = middle_value - (viewport_height / 2)
		return int(target_value)

	def _onScrollBarValueChanged(self, value: int) -> None: 
		self._goToMiddle()
		if self._program_update: 
			return
		if not self._is_scrolling:
			self._is_scrolling = True
			self._updateAllWidgets(is_special=False)
		self._stop_timer.start()

	def _setVerticalScrollBarValue(self, value: int, animation: bool=True) -> None: 
		original_program_update = self._program_update
		self._program_update = animation
		vertical_scrollbar = self.verticalScrollBar()
		assert vertical_scrollbar is not None
		vertical_scrollbar.setValue(value)
		self._program_update = original_program_update

	def _getMiddleValue(self, value: int) -> int: 
		assert self.normal_height is not None
		half_viewport_height = self._getViewportHeight() / 2
		pad_height = self.normal_height * self._num_pad
		block_height = self.normal_height * self._num_line
		if value + half_viewport_height < pad_height: 
			return value + block_height
		elif value + half_viewport_height >= block_height + pad_height: 
			return value - block_height
		else: 
			return value
  
	def _goToMiddle(self) -> None: 
		assert self.normal_height is not None
		current_value = self._getCurrentValue()
		self._setVerticalScrollBarValue(self._getMiddleValue(current_value))

	def _onScrollStop(self) -> None: 
		self._program_update = False
		self._is_scrolling = False
		self._stop_timer.stop()

		self._current_index = self._getCurrentIndex()
		self._updateAllWidgets(is_special=True, special_index=self._current_index + self._num_pad)
		self._setVerticalScrollBarValue(self._getTargetScrollValue(self._current_index))
		self.music_selected.emit(self.music_list.iloc[self._current_index]["id_musics"]) 

	def getCurrentMusicId(self) -> int: 
		item = self.item(self._current_index + self._num_pad)
		if item is None: 
			return 0
		widget: QStackedWidget = self.itemWidget(item)
		assert widget is not None
		card: BasicCard = widget.currentWidget()
		assert card is not None
		return card.music_id

	def resizeEvent(self, event: QResizeEvent) -> None: 
		self._setEmptyLabelPosition()
		super().resizeEvent(event)
		self._update_timer.start()

	def _updateAllContainerWidths(self) -> None: 
		available_width = self._getAvailableWidth()

		for i in range(self.count()): 
			item = self.item(i)
			assert item is not None
			container: QStackedWidget = self.itemWidget(item)
			assert container is not None
			container.setFixedWidth(available_width)

			current_hint = item.sizeHint()
			if current_hint.width() != available_width: 
				item.setSizeHint(QSize(available_width, current_hint.height()))

		viewport = self.viewport()
		assert viewport is not None
		viewport.update()

	def _fromMusicIdToIndex(self, music_id: int) -> int: 
		if len(self.music_list) == 0: 
			return 0
		music_list_reset: pd.DataFrame = self.music_list.reset_index()
		mask = (music_list_reset["id_musics"] == music_id)
		if mask.any(): 
			index = music_list_reset.loc[mask, "index"].iloc[0]
		else: 
			index = 0
		return index

	def randomSmoothScrolling(self, music_id: int, laps: int=1) -> None: 
		assert self.normal_height is not None
		target_index = self._fromMusicIdToIndex(music_id)
		target_value = self._getTargetScrollValue(target_index) + laps * self.normal_height * self._num_line
		current_value = self._getCurrentValue()
		while target_value < current_value: 
			target_value += self.normal_height * self._num_line

		self._animation_scrolling.startAnimation(current_value, target_value)

	def _onAnimationValueChanged(self, value: int) -> None: 
		self._setVerticalScrollBarValue(self._getMiddleValue(value), False)

	def setMusicId(self, music_id: int) -> None: 
		self._current_index = self._fromMusicIdToIndex(music_id)
		self._setVerticalScrollBarValue(self._getTargetScrollValue(self._current_index))
		self._onScrollStop()
		

class MusicListWidget(QStackedWidget): 

	music_updated = pyqtSignal(int)
	small_percentage = 0.025
	large_percentage = 0.05
	icon_percentage = 0.10
	label_percentage = 0.10

	def __init__(self, init_height: int, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.small_height = int(init_height * self.small_percentage)
		self.large_height = int(init_height * self.large_percentage)
		self.icon_size = int(init_height * self.icon_percentage)
		self.label_size = int(init_height * self.label_percentage)
		self.empty_music_list = MusicList(self.large_height, self)
		self.addWidget(self.empty_music_list)
		self.map_dict: Dict[SongType, Dict[SortType, Dict[Union[Group, str], Dict[Difficulty, Dict[str, int]]]]] = {}

		self.normal_cache: Dict[Difficulty, 
			Dict[int, Tuple[int, str, Difficulty, int, Dict[str, str], Optional[QPixmap], Optional[QPixmap]]]
		] = {}
		self.music_cache: Dict[Difficulty, 
			Dict[int, Tuple[int, str, str, str, Difficulty, int, Dict[str, Any], Optional[QPixmap], Optional[QPixmap]]]
		] = {}

	def _getMusicListIndex(self, 
			filter_options: SongType, sort_type: SortType, group: Union[Group, str], 
			difficulty: Difficulty, search_content: str
		) -> int: 
		if filter_options not in self.map_dict: 
			self.map_dict[filter_options] = {}
		if sort_type not in self.map_dict[filter_options]: 
			self.map_dict[filter_options][sort_type] = {}
		if group not in self.map_dict[filter_options][sort_type]: 
			self.map_dict[filter_options][sort_type][group] = {}
		if difficulty not in self.map_dict[filter_options][sort_type][group]: 
			self.map_dict[filter_options][sort_type][group][difficulty] = {}
		return self.map_dict[filter_options][sort_type][group][difficulty].get(search_content, -1)

	def _setMusicListIndex(self, 
			filter_options: SongType, sort_type: SortType, group: Union[Group, str], 
			difficulty: Difficulty, search_content: str, index: int
		) -> None: 
		if filter_options not in self.map_dict: 
			self.map_dict[filter_options] = {}
		if sort_type not in self.map_dict[filter_options]: 
			self.map_dict[filter_options][sort_type] = {}
		if group not in self.map_dict[filter_options][sort_type]: 
			self.map_dict[filter_options][sort_type][group] = {}
		if difficulty not in self.map_dict[filter_options][sort_type][group]: 
			self.map_dict[filter_options][sort_type][group][difficulty] = {}
		self.map_dict[filter_options][sort_type][group][difficulty][search_content] = index

	def getCurrentMusicId(self) -> int: 
		current_list: MusicList = self.currentWidget()
		if current_list is None: 
			return 0
		return current_list.getCurrentMusicId()

	def setCurrentMusicId(self, music_id: int) -> None: 
		current_list: MusicList = self.currentWidget()
		if current_list is not None: 
			current_list.setMusicId(music_id)

	def _selectVocal(self, music_id: int, vocal_table: pd.DataFrame) -> str: 
		vocal_rows: pd.DataFrame = vocal_table[vocal_table["musicId"] == music_id]
		sekai_ver: pd.DataFrame = vocal_rows[vocal_rows["caption"] == "セカイver."]
		if not sekai_ver.empty: 
			return sekai_ver.iloc[0]["vocal"]
		vs_ver: pd.DataFrame = vocal_rows[vocal_rows["caption"] == "バーチャル・シンガーver."]
		if not vs_ver.empty: 
			return vs_ver.iloc[0]["vocal"]
		inst_ver: pd.DataFrame = vocal_rows[vocal_rows["caption"] == "Inst.ver."]
		if not inst_ver.empty:
			return inst_ver.iloc[0]["vocal"]
		return vocal_rows.iloc[0]["vocal"] if not vocal_rows.empty else "Unknown"

	def _createCard(self, 
			row: pd.Series, vocal_table: pd.DataFrame, is_music_card: bool, 
			difficulty: Difficulty, config: Dict[str, Any], 
			get_cover_func: Callable[[int], Optional[np.ndarray]]
		) -> QWidget: 
		music_id = row["id_musics"]
		if is_music_card: 
			if difficulty not in self.music_cache: 
				self.music_cache[difficulty] = {}
			if music_id in self.music_cache[difficulty]: 
				cached_data = self.music_cache[difficulty][music_id]
				scaled_pixmap = None if cached_data[7] is None else cached_data[7].copy()
				pixmap = None if cached_data[8] is None else cached_data[8].copy()
				return MusicCard(
					self.small_height, self.large_height, self.icon_size, self.label_size, 
					cached_data[0], cached_data[1], cached_data[2], cached_data[3], cached_data[4], 
					cached_data[5], cached_data[6], scaled_pixmap, pixmap
				)
			else: 
				title = row["title"]
				cover = get_cover_func(int(music_id))
				composer = row["artistsName"]
				vocal = self._selectVocal(music_id, vocal_table)
				level = row["playLevel"]
				card = MusicCard(
					self.small_height, self.large_height, self.icon_size, self.label_size, 
					music_id, title, composer, vocal, difficulty, level, config, cover, None
				)
				self.music_cache[difficulty][music_id] = card.getData()
				return card
		else: 
			if difficulty not in self.normal_cache: 
				self.normal_cache[difficulty] = {}
			if music_id in self.normal_cache[difficulty]: 
				cached_data = self.normal_cache[difficulty][music_id]
				scaled_pixmap = None if cached_data[5] is None else cached_data[5].copy()
				pixmap = None if cached_data[6] is None else cached_data[6].copy()
				return NormalCard(
					self.small_height, self.large_height, self.icon_size, self.label_size, 
					cached_data[0], cached_data[1], cached_data[2], 
					cached_data[3], cached_data[4], scaled_pixmap, pixmap
				)
			else: 
				title = row["title"]
				cover = get_cover_func(int(music_id))
				level = row["playLevel"]
				card = NormalCard(
					self.small_height, self.large_height, self.icon_size, self.label_size, 
					music_id, title, difficulty, level, config, cover, None
				)
				self.normal_cache[difficulty][music_id] = card.getData()
				return card

	def _createContainer(self, row: pd.Series, vocal_table: pd.DataFrame, 
			difficulty: Difficulty, config: Dict[str, Any], 
			get_cover_func: Callable[[int], Optional[np.ndarray]], 
			normal_height: Optional[int]=None, music_height: Optional[int]=None
		) -> Tuple[QStackedWidget, int, int]: 
		container = QStackedWidget()
		container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
		normal_card = self._createCard(
			row, vocal_table, is_music_card=False, difficulty=difficulty, config=config, get_cover_func=get_cover_func
		)
		music_card = self._createCard(
			row, vocal_table, is_music_card=True, difficulty=difficulty, config=config, get_cover_func=get_cover_func
		)
		if normal_height is None: 
			normal_height = normal_card.sizeHint().height()
		if music_height is None: 
			music_height = music_card.sizeHint().height()
		container.addWidget(normal_card)
		container.addWidget(music_card)
		return container, normal_height, music_height

	def appendList(self, 
			sort_type: SortType, group: Union[Group, str], difficulty: Difficulty, search_content: str, 
			filter_options: SongType, 
			music_list: pd.DataFrame, vocal_list: pd.DataFrame, config: Dict[str, Any], 
			get_cover_func: Callable[[int], Optional[np.ndarray]]
		) -> int: 
		index = self._getMusicListIndex(
			filter_options, sort_type, group, difficulty, search_content
		)
		if index != -1: 
			return index

		if len(music_list) == 0: 
			return 0
		
		new_music_list = MusicList(self.large_height, self)
		new_music_list.refreshData(
			music_list, vocal_list, difficulty, config,
			get_cover_func=get_cover_func, 
			create_container=self._createContainer
		)
		new_music_list.music_selected.connect(self.music_updated.emit)

		self._setMusicListIndex(filter_options, sort_type, group, difficulty, search_content, self.count())
		self.addWidget(new_music_list)
		return self.count() - 1

	def switchList(self, 
			sort_type: SortType, group: Union[Group, str], difficulty: Difficulty, search_content: str, 
			filter_options: SongType, 
			music_list: pd.DataFrame, vocal_list: pd.DataFrame, config: Dict[str, Any], 
			get_cover_func: Callable[[int], Optional[np.ndarray]], music_id: int = 0
		) -> None: 
		if music_id == 0: 
			music_id = self.getCurrentMusicId()
		index = self.appendList(
			sort_type, group, difficulty, search_content, filter_options, 
			music_list, vocal_list, config, get_cover_func
		)
		self.setCurrentIndex(index)
		if index > 0: 
			self.setCurrentMusicId(music_id)

	def updateDisplayCard(self, difficulty: Difficulty, card: DisplayCard) -> None: 
		music_id = self.getCurrentMusicId()
		if music_id == 0: 
			card.updateData("", "", "", None)
			return
		data = self.music_cache[difficulty][music_id]
		pixmap = None if data[8] is None else data[8].copy()
		card.updateData(data[1], data[2], data[3], pixmap)

	def randomSmoothScrolling(self, music_id: int) -> None: 
		current_list: MusicList = self.currentWidget()
		if current_list is not None: 
			current_list.randomSmoothScrolling(music_id)

	def getCurrentMusicList(self) -> pd.DataFrame: 
		current_list: MusicList = self.currentWidget()
		if current_list is not None: 
			return current_list.music_list
		return pd.DataFrame()

	def getCachedMusicList(self, 
			sort_type: SortType, group: Union[Group, str], difficulty: Difficulty, search_content: str, 
			filter_options: SongType
		) -> Optional[pd.DataFrame]: 
		index = self._getMusicListIndex(
			filter_options, sort_type, group, difficulty, search_content
		)
		if index == -1: 
			return None
		music_list_widget: MusicList = self.widget(index)
		if music_list_widget is not None: 
			return music_list_widget.music_list
		return None

	def updateCurrentMusicWidget(self) -> None: 
		current_list: MusicList = self.currentWidget()
		if current_list is not None: 
			current_list._onScrollStop()