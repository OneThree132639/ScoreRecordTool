import logging
import json
import numpy as np
import os
import pandas as pd
import sys
import zipfile

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PyQt5.QtCore import (
	pyqtSignal, QDir, QEvent, QObject, QRect, Qt, QTimer
)
from PyQt5.QtGui import (
	QColor, QKeyEvent, QMouseEvent
)
from PyQt5.QtWidgets import (
	QDialog, QFileDialog, QHBoxLayout, QMainWindow, 
	QMessageBox, QVBoxLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from DataManager.DataManager import DataManager
	from GUI.Basics.BasicClass import GeneralClickButton, OptionCheckBox
	from GUI.Basics.Enums.Difficulty import Difficulty
	from GUI.Basics.Enums.Group import Group
	from GUI.Basics.Enums.FilterOptions import SongType
	from GUI.Basics.Enums.SortType import SortType
	from GUI.Dialog import centerDialog
	from GUI.Dialog import MessageObject, ProgressObject, UpdateController
	from GUI.DifficultyButton import DifficultyButtonSet
	from GUI.FilterDialog import FilterButton
	from GUI.GroupButton import GroupButtonSet, GroupButtonWidget
	from GUI.LineEditor import CustomListTitleBox, SearchBox
	from GUI.MusicList import DisplayCard, MusicListWidget
	from GUI.RandomDialog import RandomWidget
	from GUI.SortTypeBox import SortTypeBox
else: 
	from .DataManager.DataManager import DataManager
	from .GUI.Basics.BasicClass import GeneralClickButton, OptionCheckBox
	from .GUI.Basics.Enums.Difficulty import Difficulty
	from .GUI.Basics.Enums.Group import Group
	from .GUI.Basics.Enums.FilterOptions import SongType
	from .GUI.Basics.Enums.SortType import SortType
	from .GUI.Dialog import centerDialog
	from .GUI.Dialog import MessageObject, ProgressObject, UpdateController
	from .GUI.DifficultyButton import DifficultyButtonSet
	from .GUI.FilterDialog import FilterButton
	from .GUI.GroupButton import GroupButtonSet, GroupButtonWidget
	from .GUI.LineEditor import CustomListTitleBox, SearchBox
	from .GUI.MusicList import DisplayCard, MusicListWidget
	from .GUI.RandomDialog import RandomWidget
	from .GUI.SortTypeBox import SortTypeBox

class PublicMembers: 

	width_height_ratio = 1.5
	height_percentage = 0.8

	group_percentage = 0.1
	search_box_height_percentage = 0.025
	music_list_widget_height_percentage = 0.93
	filter_size_percentage = 0.05
	sort_type_box_height_percentage = 0.025
	diff_button_size_percentage = 0.07

	@classmethod
	def _filterByUnit(cls, music_list: Optional[pd.DataFrame], music_tags: Optional[pd.DataFrame], group: Group) -> pd.DataFrame: 
		assert music_list is not None
		assert music_tags is not None 
		mapping = {
			Group.ALL: 0, Group.VS: 1, Group.LN: 6, Group.MMJ: 4, Group.VBS: 3, Group.WS: 2, Group.NG: 5, Group.OTHER: 7
		}
		music_ids = music_tags[music_tags["seq"] == mapping[group]]["musicId"].unique()
		return music_list[music_list["id_musics"].isin(music_ids)]

	@classmethod
	def _filterByCustomGroup(cls, music_list: pd.DataFrame, custom_config: List[Dict[str, Any]], group: str) -> pd.DataFrame: 
		result = next((item for item in custom_config if item["title"] == group), None)
		if result is None:
			logging.error("Custom group '%s' not found in custom-groups.", group)
			raise ValueError(f"Custom group '{group}' not found in custom-groups.")
		filter_df = pd.DataFrame(result["id-diff-list"], columns=["id_musics", "musicDifficulty"])
		merge_result = pd.merge(music_list, filter_df, on=["id_musics", "musicDifficulty"], how="inner")
		return merge_result

	@classmethod
	def _filterByFilterOptions(cls, 
			music_list: pd.DataFrame, music_table: Optional[pd.DataFrame], filter_option: SongType
		) -> pd.DataFrame: 
		assert music_table is not None
		match filter_option: 
			case SongType.ALL: 
				pass
			case SongType.COMMISSIONED: 
				music_list = music_list[(music_list["seq"] // 100000).isin((17, 21, 22, 23, 24, 25, 26, 27))]
			case SongType.HAS_APPEND: 
				music_ids = music_table[music_table["musicDifficulty"] == "append"]["id_musics"].unique()
				music_list = music_list[music_list["id_musics"].isin(music_ids)]
		return music_list

	@classmethod
	def _filterBySearchContent(cls, music_list: pd.DataFrame, search_content: str) -> pd.DataFrame: 
		bool_df: pd.DataFrame = music_list[[
			"title", "pronunciation", "pronunciationKatakana", "lyricist", "composer", 
			"arranger", "artistsName", "artistsPronunciation", "artistsPronunciationKatakana"
			
		]].apply(lambda col: col.astype(str).str.contains(search_content, na=False))
		mask: pd.Series= bool_df.any(axis=1)
		result: pd.DataFrame = music_list[mask]
		return result

	@classmethod
	def _getMusicLevels(cls, 
			music_table: Optional[pd.DataFrame], music_id: int
		) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]: 
		if music_id == 0: 
			return (None, None, None, None, None, None)
		assert music_table is not None
		diff_list: pd.DataFrame = music_table.copy()
		diff_list = diff_list[diff_list["id_musics"] == music_id].set_index("musicDifficulty")
		diffs = ("easy", "normal", "hard", "expert", "master", "append")
		difficulties = tuple(diff_list.loc[diff, "playLevel"] if diff in diff_list.index else None for diff in diffs)
		return difficulties # type: ignore

	@classmethod
	def _recursivelyInstallEventFilter(cls, parent: QWidget, widget: QWidget) -> None: 
		stack = [widget]
		while stack: 
			current_widget = stack.pop()
			current_widget.installEventFilter(parent)
			for child in current_widget.findChildren(QWidget): 
				stack.append(child)

class ArrowKeyFilter(QObject): 

	def __init__(self, music_list_widget: MusicListWidget, 
			group_buttons: Union[GroupButtonSet, GroupButtonWidget], 
			diff_button_set: DifficultyButtonSet, 
			music_table: Optional[pd.DataFrame], 
			refresh_func: Callable[[], None], 
			all_diff: Optional[OptionCheckBox], 
			parent: QWidget
		) -> None: 
		super().__init__(parent)
		self.music_list_widget = music_list_widget
		self.group_buttons = group_buttons
		self.diff_button_set = diff_button_set
		self.refresh_func = refresh_func
		self.music_table = music_table
		self.all_diff = all_diff

		parent.installEventFilter(self)
		self.recursivelyInstallEventFilter(self.music_list_widget)
		self.recursivelyInstallEventFilter(self.group_buttons)

	def recursivelyInstallEventFilter(self, widget: QWidget) -> None: 
		stack = [widget]
		while stack: 
			current_widget = stack.pop()
			current_widget.installEventFilter(self)
			for child in current_widget.findChildren(QWidget): 
				stack.append(child)

	def eventFilter(self, watched: QObject, event: QEvent) -> bool: 
		if event.type() == QEvent.Type.KeyPress: 
			assert isinstance(event, QKeyEvent)
			if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: # type: ignore
				if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down): 
					movement = -1 if event.key() == Qt.Key.Key_Up else 1
					self.group_buttons.moveGroup(movement)
					self.refresh_func()
					return True
			match event.key(): 
				case Qt.Key.Key_Up | Qt.Key.Key_Down: 
					movement = -1 if event.key() == Qt.Key.Key_Up else 1
					self.music_list_widget.moveIndex(movement)
					return True
				case Qt.Key.Key_Left | Qt.Key.Key_Right: 
					movement = -1 if event.key() == Qt.Key.Key_Left else 1
					current_diff_index = Difficulty.toIndex(self.diff_button_set.getDifficulty())
					difficulties = PublicMembers._getMusicLevels(self.music_table, self.music_list_widget.getCurrentMusicId())
					if all(diff is None for diff in difficulties): 
						current_diff_index = (current_diff_index + movement) % len(difficulties)
					else: 
						while True: 
							current_diff_index = (current_diff_index + movement) % len(difficulties)
							if difficulties[current_diff_index] is not None: 
								break
					self.diff_button_set.setForcedDifficulty(Difficulty.fromIndex(current_diff_index))
					self.refresh_func()
					return True
				case Qt.Key.Key_PageUp | Qt.Key.Key_PageDown: 
					movement = -1 if event.key() == Qt.Key.Key_PageUp else 1
					self.group_buttons.moveGroup(movement)
					self.refresh_func()
					return True
				case Qt.Key.Key_S | Qt.Key.Key_R: 
					checked = event.key() == Qt.Key.Key_S
					self.music_list_widget.currentCheckboxCheckedSignalEmission(checked)
					return True
				case Qt.Key.Key_A: 
					if self.all_diff is not None: 
						checked = not self.all_diff.isChecked()
						self.all_diff.setChecked(checked)
						return True
				case _: 
					return False
		return False

class ClickFilter(QObject): 

	def __init__(self, box_list: List[QWidget], parent: QWidget) -> None: 
		super().__init__(parent)
		self.box_list = box_list
		self.my_parent = parent
		parent.installEventFilter(self)

	def eventFilter(self, watched: QObject, event: QEvent) -> bool: 
		if event.type() == QEvent.Type.MouseButtonPress: 
			assert isinstance(event, QMouseEvent)
			for box in self.box_list: 
				if not box.geometry().contains(self.my_parent.mapFromGlobal(event.globalPos())): 
					box.clearFocus()
					return True
		return False
class CustomListDialog(QDialog): 

	all_diff_height_percentage = 0.05
	list_title_height_percentage = 0.025

	up_percentage = 0.93
	down_percentage = 0.05
	button_width_height_ratio = 3

	def __init__(self, 
			available_geometry: QRect, title: str, 
			group_masks: np.ndarray, group_config: Dict[str, Dict[str, str]], 
			checked_group: Union[int, str], search_init: str, 
			filter_init: str, sort_type_init: str, diff_btn_config: Dict[str, Dict[str, Dict[str, Any]]], 
			get_cover_func: Callable[[int], Optional[np.ndarray]], 
			parent: Optional[QWidget]=None
		) -> None: 
		super().__init__(parent)
		self.setWindowTitle(title)
		height = int(available_geometry.height() * PublicMembers.height_percentage)
		width = int(height * PublicMembers.width_height_ratio)
		self.resize(width, height)
		up_height = int(height * self.up_percentage)
		centerDialog(self, parent)
		self.setModal(True)

		self.music_table = pd.DataFrame()
		self.vocal_table = pd.DataFrame()
		self.music_tags = pd.DataFrame()
		self.diff_btn_config = diff_btn_config
		self.get_cover_func = get_cover_func

		self.up_layout = QHBoxLayout()
		self.down_layout = QHBoxLayout()
		self.left_layout = QVBoxLayout()
		self.middle_layout = QVBoxLayout()
		self.right_layout = QVBoxLayout()
		self.rightup_layout = QHBoxLayout()
		self.rightmiddle_layout = QVBoxLayout()
		self.rightdown_layout = QVBoxLayout()
		self.my_layout = QVBoxLayout(self)
		self.setLayout(self.my_layout)

		self.group_button_set = GroupButtonSet(
			int(PublicMembers.group_percentage * self.width()), 
			group_masks=group_masks, btn_config=group_config, 
			checked_group=checked_group, parent=self
		)
		self.left_layout.addWidget(self.group_button_set)

		button_height = int(height * self.down_percentage)
		button_width = button_height * self.button_width_height_ratio
		self.cancel_button = GeneralClickButton(button_width, button_height, QColor(255, 255, 255), "キャンセル", parent=self)
		self.accept_button = GeneralClickButton(button_width, button_height, QColor("#77EEDD"), "決定", parent=self)
		self.down_layout.addWidget(self.cancel_button)
		self.down_layout.addWidget(self.accept_button)

		self.search_box = SearchBox(
			int(PublicMembers.search_box_height_percentage * up_height), 
			search_init, self
		)
		self.music_list_widget = MusicListWidget(
			int(up_height * PublicMembers.music_list_widget_height_percentage), True, 
			get_all_diff_func=self.getAllDifficulties, parent=self
		)

		self.middle_layout.addWidget(self.search_box)
		self.middle_layout.addWidget(self.music_list_widget)

		self.filter_button = FilterButton(filter_init, int(up_height * PublicMembers.filter_size_percentage), parent=self)
		self.sort_type_box = SortTypeBox(
			int(up_height * PublicMembers.sort_type_box_height_percentage), sort_type_init, parent=self
		)
		self.rightup_layout.addWidget(self.filter_button)
		self.rightup_layout.addWidget(self.sort_type_box)

		self.display_card = DisplayCard(
			self.music_list_widget.small_height, self.music_list_widget.large_height, up_height,
			"", "", "", None, self
		)
		self.diff_button_set = DifficultyButtonSet(
			int(up_height * PublicMembers.diff_button_size_percentage), (None, None, None, None, None, None), 
			diff_btn_config, parent=self
		)
		self.rightmiddle_layout.addWidget(self.display_card)
		self.rightmiddle_layout.addWidget(self.diff_button_set)

		self.all_diff = OptionCheckBox(int(up_height * self.all_diff_height_percentage), "全難易度選択", parent=self)
		self.list_title = CustomListTitleBox(int(up_height * self.list_title_height_percentage), "", parent=self)
		self.rightdown_layout.addWidget(self.all_diff)
		self.rightdown_layout.addWidget(self.list_title)

		self.right_layout.addLayout(self.rightup_layout)
		self.right_layout.addLayout(self.rightmiddle_layout)
		self.right_layout.addLayout(self.rightdown_layout)
		self.up_layout.addLayout(self.left_layout)
		self.up_layout.addLayout(self.middle_layout)
		self.up_layout.addLayout(self.right_layout)
		self.my_layout.addLayout(self.up_layout)
		self.my_layout.addLayout(self.down_layout)

		self.cancel_button.clicked.connect(self.reject)
		self.accept_button.clicked.connect(self.accept)

		self.group_button_set.button_group.buttonClicked.connect(self.refresh)
		self.search_box.textChanged.connect(self.refresh)
		self.music_list_widget.music_updated.connect(self.refreshCurrentIndex)
		self.filter_button.filter_option_changed.connect(self.refresh)
		self.sort_type_box.currentIndexChanged.connect(self.refresh)
		self.diff_button_set.button_group.buttonClicked.connect(self.refresh)

		self.all_diff.checkbox_indicator.toggled.connect(lambda: self.music_list_widget.setAllDiff(self.all_diff.isChecked()))

		self.arrow_filter = ArrowKeyFilter(
			self.music_list_widget, self.group_button_set, self.diff_button_set, 
			self.music_table, self.refresh, self.all_diff, parent=self
		)
		self.click_filter = ClickFilter([self.search_box, self.list_title], self)
		self.installEventFilter(self)

	def initRefresh(self, 
			music_table: pd.DataFrame, vocal_table: pd.DataFrame, 
			music_tags: pd.DataFrame
		) -> None: 
		self.music_table = music_table
		self.vocal_table = vocal_table
		self.music_tags = music_tags
		self.arrow_filter.music_table = music_table

	def initLoad(self, 
			group: Group, search_content: str, filter_option: SongType, 
			sort_type: SortType, difficulty: Difficulty, music_id: int, 
			title: str="", checked_list: List[Tuple[int, str]]=[]
		) -> None: 
		self.list_title.setText(title)
		self.group_button_set.setCurrentGroup(group)
		self.search_box.setText(search_content)
		self.filter_button.setCurrentFilterOptions(filter_option)
		self.sort_type_box.setCurrentSortType(sort_type)

		self.diff_button_set.setLevels((None, None, None, None, None, None), difficulty)
		self.refresh()
		self.music_list_widget.checked_list = [(music_id, Difficulty.fromStr(difficulty)) for music_id, difficulty in checked_list]
		self.music_list_widget.updateCheckbox()
		QTimer.singleShot(0, lambda: self.music_list_widget.setCurrentMusicId(music_id))

	def _filtering(self, 
			group: Group, difficulty: Difficulty, filter_option: SongType, 
			search_content: str, sort_type: SortType
		) -> pd.DataFrame: 
		music_table: pd.DataFrame = self.music_table.copy()
		music_list: pd.DataFrame = music_table[music_table["musicDifficulty"] == difficulty.value.lower()]
		music_list = PublicMembers._filterByUnit(music_list, self.music_tags, group)
		music_list = PublicMembers._filterByFilterOptions(music_list, self.music_table, filter_option)
		music_list = PublicMembers._filterBySearchContent(music_list, search_content)

		sort_tuple = ("seq", "publishedAt", "pronunciation", "playLevel")
		sort_labels = [sort_tuple[sort_type.toIndex()], "seq"]
		sort_labels = list(dict.fromkeys(sort_labels))
		music_list = music_list.sort_values(by=sort_labels, ascending=True)

		return music_list

	def refreshCurrentIndex(self, music_id: int) -> None: 
		difficulty = self.diff_button_set.getDifficulty()
		if len(self.music_list_widget.getCurrentMusicList()) == 0: 
			difficulties = (None, None, None, None, None, None)
		else: 
			difficulties = PublicMembers._getMusicLevels(self.music_table, music_id)
		self.diff_button_set.setLevels((None, None, None, None, None, None), difficulty)
		self.diff_button_set.setLevels(difficulties, difficulty)
		self.music_list_widget.updateDisplayCard(difficulty, self.display_card)
		self.display_card.pause()
		self.display_card.resume() 

	def refresh(self) -> None: 
		sort_type = self.sort_type_box.getCurrentSortType()
		group = self.group_button_set.getCurrentGroup()
		difficulty = self.diff_button_set.getDifficulty()
		filter_options = self.filter_button.filter_dialog.getCurrentFilterOptions()
		search_content = self.search_box.text()
		music_id = self.music_list_widget.getCurrentMusicId()
		assert isinstance(group, Group)

		music_list = self._filtering(
			group, difficulty, filter_options, search_content, sort_type
		)

		if len(music_list) == 0: 
			current_index = 0
		else: 
			if music_id not in music_list["id_musics"].values: 
				current_index = 0
				music_id = music_list.iloc[current_index]["id_musics"]
			else: 
				current_index = music_list.set_index("id_musics").index.get_loc(music_id)

		difficulties = PublicMembers._getMusicLevels(self.music_table, music_id)
		vocal_list = self.vocal_table

		self.filter_button.setNormalState(search_content, filter_options)
		self.diff_button_set.setLevels((None, None, None, None, None, None), difficulty)
		if len(music_list) != 0:
			self.diff_button_set.setLevels(difficulties, difficulty)
		self.music_list_widget.switchList(
			sort_type, group, difficulty, search_content, filter_options, 
			music_list, vocal_list, self.diff_btn_config[difficulty.value.lower()]["pressed"], 
			self.get_cover_func, music_id
		)
		self.music_list_widget.updateDisplayCard(difficulty, self.display_card)
		self.display_card.pause()
		self.display_card.resume()

	def getAllDifficulties(self, music_id: int) -> List[Difficulty]: 
		music_table: pd.DataFrame = self.music_table.copy()
		diff_list: pd.DataFrame = music_table[music_table["id_musics"] == music_id]
		difficulties = [Difficulty.fromStr(diff) for diff in diff_list["musicDifficulty"].values]
		return difficulties

	def getCurrentCheckedIdDiffList(self) -> List[Tuple[int, str]]: 
		id_diff_list = self.music_list_widget.checked_list.copy()
		return [(music_id, difficulty.value.lower()) for music_id, difficulty in id_diff_list]

	def setCurrentCheckedIdDiffList(self, id_diff_list: List[Tuple[int, str]]) -> None: 
		self.music_list_widget.checked_list = [(music_id, Difficulty.fromStr(difficulty)) for music_id, difficulty in id_diff_list]
		self.music_list_widget.updateCheckbox()

	def getCurrentTitle(self) -> str: 
		return self.list_title.text()

	def setCurrentTitle(self, title: str) -> None: 
		self.list_title.setText(title)

class MainWindow(QMainWindow): 

	random_height_percentage = 0.07

	update_done = pyqtSignal()

	def __init__(self, available_geometry: QRect, 
			project_base_dir: str, 
			data_dir: str, buildin_dir: str, 
			resource_dir: str, parent: Optional[QWidget]=None
		): 
		super().__init__(parent)
		self.setWindowTitle("Score Record Tool")
		height = int(available_geometry.height() * PublicMembers.height_percentage)
		width = int(height * PublicMembers.width_height_ratio)
		self.resize(width, height)
		centerDialog(self, parent)

		self.project_base_dir = project_base_dir
		self.buildin_dir = buildin_dir
		self.data_dir = data_dir
		self.resource_dir = resource_dir
		self.config = {}
		self._loadConfig()
		self._init_config = self.config.copy()
		self.data_manager = DataManager(
			project_base_dir, data_dir, buildin_dir, resource_dir, 
			self._chooseResourceFile
		)

		self.main_widget = QWidget(self)
		self.left_layout = QVBoxLayout()
		self.middle_layout = QVBoxLayout()
		self.right_layout = QVBoxLayout()
		self.rightup_layout = QHBoxLayout()
		self.rightmiddle_layout = QVBoxLayout()
		self.rightdown_layout = QHBoxLayout()
		self.my_layout = QHBoxLayout(self.main_widget)
		self.setCentralWidget(self.main_widget)

		custom_list = [elem["title"] for elem in self._init_config.get("custom-groups", [])]
		self.group_button_widget = GroupButtonWidget(
			int(PublicMembers.group_percentage * self.width()), 
			self.data_manager.logo_array, self.data_manager.loadBinaryArray("random-setting-array"), 
			self.data_manager.config["group"], 
			checked_group=self._init_config.get("group", 0), 
			custom_list=custom_list, 
			parent=self
		)
		self.left_layout.addWidget(self.group_button_widget)

		self.search_box = SearchBox(
			int(PublicMembers.search_box_height_percentage * self.height()), 
			self._init_config.get("search", ""), parent=self
		)
		self.music_list_widget = MusicListWidget(
			int(self.height() * PublicMembers.music_list_widget_height_percentage), parent=self
		)

		self.middle_layout.addWidget(self.search_box)
		self.middle_layout.addWidget(self.music_list_widget)

		self.filter_button = FilterButton(
			self._init_config.get("filter", {}), 
			int(self.height() * PublicMembers.filter_size_percentage), parent=self
		)
		self.sort_type_box = SortTypeBox(
			int(self.height() * PublicMembers.sort_type_box_height_percentage), 
			self._init_config.get("sort_type", ""), parent=self
		)
		self.rightup_layout.addWidget(self.filter_button)
		self.rightup_layout.addWidget(self.sort_type_box)

		self.display_card = DisplayCard(
			self.music_list_widget.small_height, self.music_list_widget.large_height, self.height(),
			"", "", "", None, parent=self
		)
		self.diff_button_set = DifficultyButtonSet(
			int(self.height() * PublicMembers.diff_button_size_percentage), (None, None, None, None, None, None), 
			self.data_manager.config["button"], parent=self
		)
		self.rightmiddle_layout.addWidget(self.display_card)
		self.rightmiddle_layout.addWidget(self.diff_button_set)

		self.random_widget = RandomWidget(
			int(self.height() * self.random_height_percentage), 
			self.data_manager.loadBinaryArray, self._init_config.get("random", {}), parent=self
		)
		self.rightdown_layout.addWidget(self.random_widget)
		
		self.right_layout.addLayout(self.rightup_layout)
		self.right_layout.addLayout(self.rightmiddle_layout)
		self.right_layout.addLayout(self.rightdown_layout)
		self.my_layout.addLayout(self.left_layout)
		self.my_layout.addLayout(self.middle_layout)
		self.my_layout.addLayout(self.right_layout)

		self.custom_list_dialog = CustomListDialog(
			available_geometry, title="Custom List", 
			group_masks=self.data_manager.logo_array, group_config=self.data_manager.config["group"], 
			checked_group=self._init_config.get("group", 0), search_init=self._init_config.get("search", ""), 
			filter_init=self._init_config.get("filter", {}), sort_type_init=self._init_config.get("sort_type", ""), 
			diff_btn_config=self.data_manager.config["button"], get_cover_func=self.data_manager.getCoverArray, 
			parent=self
		)

		QTimer.singleShot(0, self.updateQuery)

		self.group_button_widget.group_button_set.button_group.buttonClicked.connect(self.refresh)
		self.search_box.textChanged.connect(self.refresh)
		self.music_list_widget.music_updated.connect(self.refreshCurrentIndex)
		self.filter_button.filter_option_changed.connect(self.refresh)
		self.sort_type_box.currentIndexChanged.connect(self.refresh)
		self.diff_button_set.button_group.buttonClicked.connect(self.refresh)
		self.random_widget.random_button.clicked.connect(self.randomRolling)

		self.group_button_widget.add_button.clicked.connect(self._onAddGroupButtonClicked)
		self.group_button_widget.sub_button.clicked.connect(self._onSubGroupButtonClicked)
		self.group_button_widget.setting_button.clicked.connect(self._onSettingGroupButtonClicked)

		self.arrow_filter = ArrowKeyFilter(
			self.music_list_widget, self.group_button_widget, self.diff_button_set, 
			self.data_manager.music_table, self.refresh, None, self
		)
		self.click_filter = ClickFilter([self.search_box], self)

	def _chooseResourceFile(self) -> bool: 
		msg_box = QMessageBox(self)
		msg_box.setIcon(QMessageBox.Icon.Question)
		msg_box.setWindowTitle("Resource File Issue")
		msg_box.setText((
			"Error occurred while loading resource file (not exist or errupted). \n"
			"Please select the up-to-date resource file (zip) to continue. "
		))
		msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel) # type: ignore
		if msg_box.exec() == QMessageBox.StandardButton.Ok: 
			file_path, _ = QFileDialog.getOpenFileName(
				self, caption="Select Resource File", 
				directory=self._init_config.get("last-resource-file-dir", QDir.homePath()), 
				filter="Zip files (*.zip)"
			)

			if file_path: 
				with zipfile.ZipFile(file_path, "r") as zip_ref: 
					zip_ref.extractall(self.project_base_dir)
				self.config["last-resource-file-dir"] = os.path.dirname(file_path)
				return True

		msg_box = QMessageBox(self)
		msg_box.setIcon(QMessageBox.Icon.Critical)
		msg_box.setWindowTitle("Error")
		msg_box.setText("Failed to load resource files. Please restart the program and try again. ") 
		msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
		centerDialog(msg_box, self)
		msg_box.exec_()
		sys.exit(1)
		return False

	def _initRefresh(self) -> None: 
		difficulty = Difficulty.fromStr(self._init_config.get("difficulty", "easy"))
		self.diff_button_set.setLevels((None, None, None, None, None, None), difficulty)
		self.refresh()
		music_id = self._init_config.get("music_id", 0)
		self.music_list_widget.setCurrentMusicId(music_id)

		music_table = self.data_manager.music_table
		vocal_table = self.data_manager.vocal_table
		music_tags = self.data_manager.musicTags
		assert music_table is not None
		assert vocal_table is not None
		assert music_tags is not None
		self.custom_list_dialog.initRefresh(music_table, vocal_table, music_tags)

	def updateQuery(self) -> None: 
		msg_box = QMessageBox(self)
		msg_box.setIcon(QMessageBox.Icon.Question)
		msg_box.setWindowTitle("Update Confirmation")
		msg_box.setText("Are you sure you want to update the data? This may take some time.")
		msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) # type: ignore
		centerDialog(msg_box, self)
		reply = msg_box.exec_()
		if reply == QMessageBox.StandardButton.Yes: 
			self.updateResources()
		else: 
			try: 
				self.data_manager.loadLocalResources()
			except FileNotFoundError as e: 
				msg_box = QMessageBox(self)
				msg_box.setIcon(QMessageBox.Icon.Critical)
				msg_box.setWindowTitle("Error")
				msg_box.setText("Failed to load local files. Please update the data first.") 
				msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
				centerDialog(msg_box, self)
				msg_box.exec_()
				sys.exit(1)
				return
			self._initRefresh()

	def updateResources(self) -> None: 
		self.update_ctrl = UpdateController(self)
		update_list: List[str] = [
			"characterProfiles", "gameCharacters", "musicArtists", "musicAssetVariants", "musicCollaborations",
			"musicDifficulties", "musics", "musicTags", "musicVocals", "outsideCharacters"
		]

		for idx, key in enumerate(update_list): 
			try: 
				task_object = MessageObject(
					idx, "Updating {}...".format(key), lambda key=key: self.data_manager.process(key)
				)
			except FileNotFoundError as e: 
				msg_box = QMessageBox(self)
				msg_box.setIcon(QMessageBox.Icon.Critical)
				msg_box.setWindowTitle("Error")
				msg_box.setText("Failed to update {}. Please check your network connection and try again.".format(key)) 
				msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
				centerDialog(msg_box, self)
				msg_box.exec_()
				sys.exit(1)
				return
			self.update_ctrl.appendTask(task_object)

		self.update_ctrl.appendTask(ProgressObject(
			len(update_list), "Covers", self.data_manager.updateCovers
		))

		self.update_ctrl.all_updates_finished.connect(self._onAllUpdatesFinished)
		self.update_ctrl.start()

	def _onAllUpdatesFinished(self) -> None: 
		logging.debug("All updates finished, building music table...")
		self.data_manager.updateMusicTable()
		self.data_manager.updateVocalTable()
		self.data_manager.saveCustomTable(self.data_manager.music_table, "musicTable.csv")
		self.data_manager.saveCustomTable(self.data_manager.vocal_table, "vocalTable.csv")

		msg_box = QMessageBox(self)
		msg_box.setWindowTitle("Update Complete")
		msg_box.setText("All updates have been completed successfully. ")
		msg_box.setIcon(QMessageBox.Icon.Information)
		msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
		msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)

		msg_box.exec_()

		self._initRefresh()

	def _filtering(self, 
			group: Union[Group, str], difficulty: Difficulty, filter_option: SongType, 
			search_content: str, sort_type: SortType
		) -> pd.DataFrame: 
		music_table: Optional[pd.DataFrame] = self.data_manager.music_table
		assert music_table is not None
		music_list: pd.DataFrame = music_table.copy()
		music_list: pd.DataFrame = music_list[music_list["musicDifficulty"] == difficulty.value.lower()]
		if isinstance(group, Group): 
			music_list = PublicMembers._filterByUnit(music_list, self.data_manager.musicTags, group)
		elif isinstance(group, str): 
			music_list = PublicMembers._filterByCustomGroup(music_list, self.config["custom-groups"], group)
		music_list = PublicMembers._filterByFilterOptions(music_list, self.data_manager.music_table, filter_option)
		music_list = PublicMembers._filterBySearchContent(music_list, search_content)

		sort_tuple = ("seq", "publishedAt", "pronunciation", "playLevel")
		sort_labels = [sort_tuple[sort_type.toIndex()], "seq"]
		sort_labels = list(dict.fromkeys(sort_labels))
		music_list = music_list.sort_values(by=sort_labels, ascending=True)

		return music_list

	def refreshCurrentIndex(self, music_id: int) -> None: 
		difficulty = self.diff_button_set.getDifficulty()
		if len(self.music_list_widget.getCurrentMusicList()) == 0: 
			difficulties = (None, None, None, None, None, None)
		else: 
			difficulties = PublicMembers._getMusicLevels(self.data_manager.music_table, music_id)
		self.diff_button_set.setLevels((None, None, None, None, None, None), difficulty)
		self.diff_button_set.setLevels(difficulties, difficulty)
		self.music_list_widget.updateDisplayCard(difficulty, self.display_card)
		self.display_card.pause()
		self.display_card.resume()
		self._saveConfig()

	def refresh(self) -> None: 
		sort_type = self.sort_type_box.getCurrentSortType()
		group = self.group_button_widget.getCurrentGroup()
		difficulty = self.diff_button_set.getDifficulty()
		filter_options = self.filter_button.filter_dialog.getCurrentFilterOptions()
		search_content = self.search_box.text()
		music_id = self.music_list_widget.getCurrentMusicId()

		music_list = self._filtering(
			group, difficulty, filter_options, search_content, sort_type
		)

		if len(music_list) == 0: 
			current_index = 0
		else: 
			if music_id not in music_list["id_musics"].values: 
				current_index = 0
				music_id = music_list.iloc[current_index]["id_musics"]
			else: 
				current_index = music_list.set_index("id_musics").index.get_loc(music_id)

		difficulties = PublicMembers._getMusicLevels(self.data_manager.music_table, music_id)
		vocal_list = self.data_manager.vocal_table
		assert vocal_list is not None

		self.filter_button.setNormalState(search_content, filter_options)
		self.diff_button_set.setLevels((None, None, None, None, None, None), difficulty)
		if len(music_list) != 0: 
			self.diff_button_set.setLevels(difficulties, difficulty)
		self.music_list_widget.switchList(
			sort_type, group, difficulty, search_content, filter_options, 
			music_list, vocal_list, self.data_manager.config["button"][difficulty.value.lower()]["pressed"], 
			self.data_manager.getCoverArray, music_id
		)
		self.music_list_widget.updateDisplayCard(difficulty, self.display_card)
		self.display_card.pause()
		self.display_card.resume()

		self._saveConfig()

	def randomRolling(self) -> None: 
		random_option = self.random_widget.setting_dialog.getCurrentOptions()
		difficulty_type, difficulties, level_range = random_option
		if difficulty_type == "現在の難易度": 
			music_list = self.music_list_widget.getCurrentMusicList().copy()
		elif difficulty_type == "複数の難易度": 
			music_list = pd.DataFrame()
			sort_type = self.sort_type_box.getCurrentSortType()
			group = self.group_button_widget.getCurrentGroup()
			filter_option = self.filter_button.getCurrentFilterOptions()
			search_content = self.search_box.text()
			vocal_table = self.data_manager.vocal_table
			assert vocal_table is not None

			for diff in difficulties: 
				diff_enum = Difficulty.fromStr(diff)
				appendant = self.music_list_widget.getCachedMusicList(
					sort_type, group, diff_enum, search_content, filter_option
				)
				if appendant is None: 
					appendant = self._filtering(group, diff_enum, filter_option, search_content, sort_type)
					self.music_list_widget.appendList(
						sort_type, group, diff_enum, search_content, filter_option, appendant, 
						vocal_table, self.data_manager.config["button"][diff_enum.value.lower()]["pressed"], 
						self.data_manager.getCoverArray
					)
				music_list = pd.concat([music_list, appendant])

		music_list: pd.DataFrame = music_list[(music_list["playLevel"] >= level_range[0]) & (music_list["playLevel"] <= level_range[1])]
		music_list.reset_index(drop=True, inplace=True)

		if music_list.empty: 
			msg_box = QMessageBox(self)
			msg_box.setIcon(QMessageBox.Icon.Warning)
			msg_box.setWindowTitle("No Music Found")
			msg_box.setText("No music found matching the specified criteria. Please adjust your settings and try again. ")
			msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
			centerDialog(msg_box, self)
			msg_box.exec_()
			return

		selected_row = music_list.sample(n=1).iloc[0]
		selected_music_id = selected_row["id_musics"]
		selected_difficulty = Difficulty.fromStr(selected_row["musicDifficulty"])

		self.diff_button_set.setLevels((None, None, None, None, None, None), selected_difficulty)
		self.refresh()
		self.music_list_widget.randomSmoothScrolling(selected_music_id)

		self._saveConfig()

	def _saveConfig(self) -> None: 
		self.config["difficulty"] = self.diff_button_set.getDifficulty().value
		self.config["filter"] = self.filter_button.getCurrentFilterOptions().value
		self.config["group"] = self.group_button_widget.getCurrentGroupConfig()
		self.config["music_id"] = self.music_list_widget.getCurrentMusicId()
		self.config["random"] = self.random_widget.setting_dialog.getCurrentOptionsConfig()
		self.config["search"] = self.search_box.text()
		self.config["sort_type"] = self.sort_type_box.currentText()

		config_path = os.path.join(self.data_dir, "config", "config.json")
		os.makedirs(os.path.dirname(config_path), exist_ok=True)
		with open(config_path, "w", encoding="utf-8") as f: 
			json.dump(self.config, f, indent=4, ensure_ascii=False)

	def _loadConfig(self) -> None: 
		config_path = os.path.join(self.data_dir, "config", "config.json")
		if os.path.exists(config_path): 
			try: 
				with open(config_path, "r", encoding="utf-8") as f: 
					self.config = json.load(f)
			except Exception as e: 
				logging.warning("Failed to load config file: %s. Using default config.", e)

	def eventFilter(self, watched: QObject, event: QEvent) -> bool: 
		if event.type() == QEvent.Type.MouseButtonPress: 
			assert isinstance(event, QMouseEvent)
			if not self.search_box.geometry().contains(self.mapFromGlobal(event.globalPos())): 
				self.search_box.clearFocus()
				return True
		if event.type() == QEvent.Type.KeyPress: 
			assert isinstance(event, QKeyEvent)
			if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right): 
				if event.key() == Qt.Key.Key_Up: 
					self.music_list_widget.moveIndex(-1)
				elif event.key() == Qt.Key.Key_Down: 
					self.music_list_widget.moveIndex(1)
				elif event.key() == Qt.Key.Key_Left: 
					current_diff_index = Difficulty.toIndex(self.diff_button_set.getDifficulty())
					difficulties = PublicMembers._getMusicLevels(self.data_manager.music_table, self.music_list_widget.getCurrentMusicId())
					if all(diff is None for diff in difficulties): 
						current_diff_index = (current_diff_index - 1) % len(difficulties)
					else: 
						while True: 
							current_diff_index = (current_diff_index - 1) % len(difficulties)
							if difficulties[current_diff_index] is not None: 
								break
					self.diff_button_set.setForcedDifficulty(Difficulty.fromIndex(current_diff_index))
					self.refresh()
				elif event.key() == Qt.Key.Key_Right: 
					current_diff_index = Difficulty.toIndex(self.diff_button_set.getDifficulty())
					difficulties = PublicMembers._getMusicLevels(self.data_manager.music_table, self.music_list_widget.getCurrentMusicId())
					if all(diff is None for diff in difficulties): 
						current_diff_index = (current_diff_index + 1) % len(difficulties)
					else: 
						while True: 
							current_diff_index = (current_diff_index + 1) % len(difficulties)
							if difficulties[current_diff_index] is not None: 
								break
					self.diff_button_set.setForcedDifficulty(Difficulty.fromIndex(current_diff_index))
					self.refresh()
				return True
		return super().eventFilter(watched, event)

	def _onAddGroupButtonClicked(self) -> None: 
		group = self.group_button_widget.getCurrentGroup()
		if not isinstance(group, Group): 
			group = Group.ALL
		self.custom_list_dialog.initLoad(
			group, 
			self.search_box.text(), self.filter_button.getCurrentFilterOptions(), 
			self.sort_type_box.getCurrentSortType(), self.diff_button_set.getDifficulty(), 
			self.music_list_widget.getCurrentMusicId()
		)
		while True: 
			if self.custom_list_dialog.exec() == QDialog.DialogCode.Accepted: 
				if "custom-groups" not in self.config: 
					self.config["custom-groups"] = []
				title = self.custom_list_dialog.getCurrentTitle()
				if not title: 
					msg = QMessageBox(self)
					msg.setIcon(QMessageBox.Icon.Warning)
					msg.setWindowTitle("Invalid Title")
					msg.setText("The title for the custom group cannot be empty. Please enter a valid title.")
					msg.setStandardButtons(QMessageBox.StandardButton.Ok)
					centerDialog(msg, self)
					msg.exec_()
					continue
				elif title in self.config["custom-groups"]: 
					msg = QMessageBox(self)
					msg.setIcon(QMessageBox.Icon.Warning)
					msg.setWindowTitle("Duplicate Title")
					msg.setText(f"The title '{title}' already exists. Please enter a different title.")
					msg.setStandardButtons(QMessageBox.StandardButton.Ok)
					centerDialog(msg, self)
					msg.exec_()
					continue
				self.config["custom-groups"].append({
					"title": title, 
					"id-diff-list": self.custom_list_dialog.getCurrentCheckedIdDiffList()
				}) 
				self.group_button_widget.addButton(title) 
			break

		self._saveConfig()

	def _onSubGroupButtonClicked(self) -> None: 
		group = self.group_button_widget.getCurrentGroup()
		assert isinstance(group, str)
		msg = QMessageBox(self)
		msg.setIcon(QMessageBox.Icon.Question)
		msg.setWindowTitle("Delete Custom Group")
		msg.setText(f"Are you sure you want to delete the custom group '{group}'? This action cannot be undone.")
		msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) # type: ignore
		centerDialog(msg, self)
		if msg.exec() == QMessageBox.StandardButton.Yes:
			self.group_button_widget.removeButton(group)
			self.config["custom-groups"].remove(next((item for item in self.config["custom-groups"] if item["title"] == group), None))
			self.group_button_widget.group_button_set.setCurrentGroup(Group.ALL)
			self.group_button_widget._onGroupButtonClicked()
			self.refresh()
			self.music_list_widget.removeListByGroup(group)
		self._saveConfig()

	def _onSettingGroupButtonClicked(self) -> None: 
		group = self.group_button_widget.getCurrentGroup()
		assert isinstance(group, str)
		index, group_dict = next(
			((idx, item) for idx, item in enumerate(self.config["custom-groups"]) 
			if item["title"] == group), (None, None)
		)
		assert group_dict is not None
		origin_title = group_dict["title"]
		self.custom_list_dialog.initLoad(
			Group.ALL, 
			self.search_box.text(), self.filter_button.getCurrentFilterOptions(), 
			self.sort_type_box.getCurrentSortType(), self.diff_button_set.getDifficulty(), 
			self.music_list_widget.getCurrentMusicId(), title=group, 
			checked_list=group_dict["id-diff-list"]
		)
		while True: 
			if self.custom_list_dialog.exec() == QDialog.DialogCode.Accepted: 
				if "custom-groups" not in self.config: 
					self.config["custom-groups"] = []
				title = self.custom_list_dialog.getCurrentTitle()
				if not title: 
					msg = QMessageBox(self)
					msg.setIcon(QMessageBox.Icon.Warning)
					msg.setWindowTitle("Invalid Title")
					msg.setText("The title for the custom group cannot be empty. Please enter a valid title.")
					msg.setStandardButtons(QMessageBox.StandardButton.Ok)
					centerDialog(msg, self)
					msg.exec_()
					continue
				elif title in self.config["custom-groups"]: 
					msg = QMessageBox(self)
					msg.setIcon(QMessageBox.Icon.Warning)
					msg.setWindowTitle("Duplicate Title")
					msg.setText(f"The title '{title}' already exists. Please enter a different title.")
					msg.setStandardButtons(QMessageBox.StandardButton.Ok)
					centerDialog(msg, self)
					msg.exec_()
					continue
				self.music_list_widget.removeListByGroup(group)
				self.config["custom-groups"][index] = {
					"title": title, 
					"id-diff-list": self.custom_list_dialog.getCurrentCheckedIdDiffList()
				} 
				self.group_button_widget.renameButton(origin_title, title)
				self.group_button_widget.group_button_set.setCurrentGroup(title)
				self.group_button_widget._onGroupButtonClicked()
				self.refresh()
			break

		self._saveConfig()
