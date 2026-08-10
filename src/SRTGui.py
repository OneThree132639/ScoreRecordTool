import logging
import pandas as pd
import time

from typing import Dict, List, Optional, Tuple, Union

from PyQt5.QtCore import (
	pyqtSignal, QTimer
)
from PyQt5.QtWidgets import (
	QApplication, QHBoxLayout, QMainWindow, QMessageBox, QVBoxLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from DataManager.DataManager import DataManager
	from GUI.Basics.Enums.Difficulty import Difficulty
	from GUI.Basics.Enums.Group import Group
	from GUI.Dialog import centerDialog
	from GUI.Dialog import MessageObject, ProgressObject, UpdateController
	from GUI.DifficultyButton import DifficultyButtonSet
	from GUI.FilterDialog import FilterButton
	from GUI.GroupButton import GroupButtonSet
	from GUI.MusicList import DisplayCard, MusicList
	from GUI.RandomDialog import RandomWidget
	from GUI.SearchBox import SearchBox
	from GUI.SortTypeBox import SortTypeBox
else: 
	from .DataManager.DataManager import DataManager
	from .GUI.Basics.Enums.Difficulty import Difficulty
	from .GUI.Basics.Enums.Group import Group
	from .GUI.Dialog import centerDialog
	from .GUI.Dialog import MessageObject, ProgressObject, UpdateController
	from .GUI.DifficultyButton import DifficultyButtonSet
	from .GUI.FilterDialog import FilterButton
	from .GUI.GroupButton import GroupButtonSet
	from .GUI.MusicList import DisplayCard, MusicList
	from .GUI.RandomDialog import RandomWidget
	from .GUI.SearchBox import SearchBox
	from .GUI.SortTypeBox import SortTypeBox

class Cache: 

	def __init__(self) -> None: 
		self.music_id = 1
		self.index = 0
		self.filter_option = "すべて"
		self.search_content = ""
		self.random_option: Tuple[str, List[str], Tuple[int, int]] = ("現在の難易度", [], (5, 38))
		self.group: Union[Group, str] = Group.ALL
		self.difficulty = Difficulty.EASY
		self.music_list = pd.DataFrame()

		self.list_cache: Dict[Union[Group, str], Dict[Difficulty, pd.DataFrame]] = {}

class MainWindow(QMainWindow): 

	filter_button_size = 30
	group_size = 50
	update_done = pyqtSignal()

	def __init__(self, data_dir: str, buildin_dir: str, 
			resource_dir: str, parent: Optional[QWidget]=None
		): 
		super().__init__(parent)
		self.setWindowTitle("Score Record Tool")
		self.resize(1000, 600)

		self.cache = Cache()

		self.buildin_dir = buildin_dir
		self.data_dir = data_dir
		self.resource_dir = resource_dir
		self.data_manager = DataManager(data_dir, buildin_dir, resource_dir)

		main_widget = QWidget(self)
		self.left_layout = QVBoxLayout()
		self.middle_layout = QVBoxLayout()
		self.right_layout = QVBoxLayout()
		self.rightup_layout = QHBoxLayout()
		self.rightmiddle_layout = QVBoxLayout()
		self.rightdown_layout = QHBoxLayout()
		self.my_layout = QHBoxLayout(main_widget)
		self.setCentralWidget(main_widget)

		self.group_button_set = GroupButtonSet(self.group_size, 
			self.data_manager.logo_array, self.data_manager.config["group"]
		)
		self.left_layout.addWidget(self.group_button_set)

		self.search_box = SearchBox(self)
		self.music_list = MusicList(self)
		self.middle_layout.addWidget(self.search_box)
		self.middle_layout.addWidget(self.music_list)

		self.filter_button = FilterButton(self.filter_button_size, self)
		self.sort_type_box = SortTypeBox(self)
		self.rightup_layout.addWidget(self.filter_button)
		self.rightup_layout.addWidget(self.sort_type_box)

		self.display_card = DisplayCard("", "", "", None, self)
		self.diff_button_set = DifficultyButtonSet(
			50, (None, None, None, None, None, None), 
			self.data_manager.config["button"], self
		)
		self.rightmiddle_layout.addWidget(self.display_card)
		self.rightmiddle_layout.addWidget(self.diff_button_set)

		self.random_widget = RandomWidget(self.data_manager.loadBinaryArray, self)
		self.rightdown_layout.addWidget(self.random_widget)
		
		self.right_layout.addLayout(self.rightup_layout)
		self.right_layout.addLayout(self.rightmiddle_layout)
		self.right_layout.addLayout(self.rightdown_layout)
		self.my_layout.addLayout(self.left_layout)
		self.my_layout.addLayout(self.middle_layout)
		self.my_layout.addLayout(self.right_layout)

		QTimer.singleShot(0, self.updateQuery)

		self.group_button_set.button_group.buttonClicked.connect(self.refresh)
		self.search_box.textChanged.connect(self.refresh)
		self.music_list.music_selected.connect(self.refreshCurrentIndex)
		self.filter_button.filter_option_changed.connect(self.refresh)
		self.sort_type_box.currentIndexChanged.connect(self.refresh)
		self.diff_button_set.button_group.buttonClicked.connect(self.refresh)
		self.random_widget.random_button.clicked.connect(self.randomRolling)

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
				msg_box.setText("Failed to load local resources. Please update the data first.") 
				msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
				centerDialog(msg_box, self)
				msg_box.exec_()
				QApplication.quit()
				return
			self.refresh()

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
				QApplication.quit()
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

		self.refresh()

	def _filterByUnit(self, music_list: pd.DataFrame, group: Group) -> pd.DataFrame: 
		music_tags = self.data_manager.musicTags
		assert music_tags is not None
		mapping = {
			Group.ALL: 0, Group.VS: 1, Group.LN: 6, Group.MMJ: 4, Group.VBS: 3, Group.WS: 2, Group.NG: 5, Group.OTHER: 7
		}
		music_ids = music_tags[music_tags["seq"] == mapping[group]]["musicId"].unique()
		return music_list[music_list["id_musics"].isin(music_ids)]

	def _filterByCustomGroup(self, music_list: pd.DataFrame, group: str) -> pd.DataFrame: 
		if group not in self.data_manager.custom_list: 
			logging.error("Custom group '%s' not found in custom_list.", group)
			raise ValueError(f"Custom group '{group}' not found in custom_list.")
		music_ids = self.data_manager.custom_list[group]
		return music_list[music_list["id_musics"].isin(music_ids)]

	def _filterByFilterOptions(self, music_list: pd.DataFrame, filter_option: str) -> pd.DataFrame: 
		match filter_option: 
			case "すべて": 
				pass
			case "書き下ろし楽曲": 
				music_list = music_list[(music_list["seq"] // 100000).isin((17, 21, 22, 23, 24, 25, 26, 27))]
			case "APPENDあり": 
				music_ids = music_list[music_list["musicDifficulty"] == "append"]["id_musics"].unique()
				music_list = music_list[music_list["id_musics"].isin(music_ids)]
		return music_list

	def _filterBySearchContent(self, music_list: pd.DataFrame, search_content: str) -> pd.DataFrame: 
		bool_df: pd.DataFrame = music_list[[
			"title", "pronunciation", "pronunciationKatakana", "lyricist", "composer", 
			"arranger", "artistsName", "artistsPronunciation", "artistsPronunciationKatakana"
			
		]].apply(lambda col: col.astype(str).str.contains(search_content, na=False))
		mask: pd.Series= bool_df.any(axis=1)
		result: pd.DataFrame = music_list[mask]
		return result

	def _getGroupDifficultyMusicList(self, group: Union[Group, str], difficulty: Difficulty) -> pd.DataFrame: 
		if group not in self.cache.list_cache: 
			self.cache.list_cache[group] = {}
		if difficulty not in self.cache.list_cache[group]: 
			music_table = self.data_manager.music_table
			assert music_table is not None
			music_list = music_table.copy()
			if isinstance(group, Group): 
				music_list = self._filterByUnit(music_list, group)
			elif isinstance(group, str): 
				music_list = self._filterByCustomGroup(music_list, group)
			music_list: pd.DataFrame = music_list[music_list["musicDifficulty"] == difficulty.value.lower()]
			self.cache.list_cache[group][difficulty] = music_list
		return self.cache.list_cache[group][difficulty]

	def _getMusicLevels(self, music_id: int) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]: 
		music_table = self.data_manager.music_table
		assert music_table is not None
		diff_list: pd.DataFrame = music_table.copy()
		diff_list = diff_list[diff_list["id_musics"] == music_id].set_index("musicDifficulty")
		diffs = ("easy", "normal", "hard", "expert", "master", "append")
		difficulties = tuple(diff_list.loc[diff, "playLevel"] if diff in diff_list.index else None for diff in diffs)
		return difficulties # type: ignore

	def refreshCurrentIndex(self, index: int) -> None: 
		difficulty = self.cache.difficulty
		if len(self.cache.music_list) == 0: 
			difficulties = (None, None, None, None, None, None)
		else: 
			self.cache.music_id = self.cache.music_list.iloc[index]["id_musics"]
			difficulties = self._getMusicLevels(self.cache.music_id)
		self.diff_button_set.setLevels(difficulties, difficulty) # type: ignore
		self.music_list.updateDisplayCard(difficulty, self.display_card)
		self.display_card.pause()
		self.display_card.resume()

	def refresh(self) -> None: 
		group = self.group_button_set.getCurrentGroup()
		difficulty = self.diff_button_set.getDifficulty()
		filter_option = self.filter_button.filter_dialog.getCurrentFilterOptions()
		search_content = self.search_box.text()
		music_id = self.music_list.getCurrentMusicId()
		current_index = self.music_list._getCurrentIndex()

		music_list = self._getGroupDifficultyMusicList(group, difficulty)
		music_list: pd.DataFrame = self._filterByFilterOptions(music_list, filter_option)
		music_list: pd.DataFrame = music_list[music_list["publishedAt"] < int(time.time() * 1000)]
		sort_tuple = ("seq", "publishedAt", "pronunciation", "playLevel")
		sort_labels = [sort_tuple[self.sort_type_box.currentIndex()], "seq"]
		sort_labels = list(dict.fromkeys(sort_labels))
		music_list.sort_values(by=sort_labels, ascending=True, inplace=True)
		music_list = self._filterBySearchContent(music_list, search_content)

		if len(music_list) == 0: 
			current_index = 0
		else: 
			if music_id not in music_list["id_musics"].values: 
				current_index = 0
				music_id = music_list.iloc[current_index]["id_musics"]
			else: 
				current_index = music_list.set_index("id_musics").index.get_loc(music_id)

		self.cache.music_list = music_list
		self.cache.index = current_index
		self.cache.music_id = music_id
		self.cache.search_content = search_content
		self.cache.filter_option = filter_option
		self.cache.group = group
		self.cache.difficulty = difficulty

		difficulties = self._getMusicLevels(music_id)

		self.music_list.refreshData(
			music_list, self.data_manager.vocal_table, current_index, 
			difficulty, self.data_manager.config["button"][difficulty.value.lower()]["pressed"], 
			self.data_manager.getCoverArray
		)
		self.diff_button_set.setLevels(difficulties, difficulty) # type: ignore
		self.music_list.updateDisplayCard(difficulty, self.display_card)
		self.display_card.pause()
		self.display_card.resume()

	def randomRolling(self) -> None: 
		self.cache.random_option = self.random_widget.setting_dialog.getCurrentOptions()
		difficulty_type, difficulties, level_range = self.cache.random_option
		if difficulty_type == "現在の難易度": 
			difficulty = self.cache.difficulty
			music_list = self._getGroupDifficultyMusicList(self.cache.group, difficulty)
		elif difficulty_type == "複数の難易度": 
			music_list = pd.DataFrame()
			for diff in difficulties: 
				diff_enum = Difficulty.fromStr(diff)
				music_list = pd.concat([music_list, self._getGroupDifficultyMusicList(self.cache.group, diff_enum)])
		music_list = self._filterByFilterOptions(music_list, self.cache.filter_option)
		music_list: pd.DataFrame = music_list[
			(level_range[0] <= music_list["playLevel"]) & (music_list["playLevel"] <= level_range[1])
		]
		music_list = self._filterBySearchContent(music_list, self.cache.search_content)

		selected_row = music_list.sample(n=1).iloc[0]
		selected_music_id = selected_row["id_musics"]
		selected_difficulty = Difficulty.fromStr(selected_row["musicDifficulty"])

		self.diff_button_set.setLevels(self._getMusicLevels(selected_music_id), selected_difficulty)
		self.diff_button_set.setCheckedDifficulty(selected_difficulty)
		self.cache.difficulty = selected_difficulty
		self.cache.music_id = selected_music_id
		self.refresh()
		index = self.cache.music_list.set_index("id_musics").index.get_loc(selected_music_id)
		self.music_list.randomSmoothScrolling(index)

