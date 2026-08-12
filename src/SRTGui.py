import logging
import json
import os
import pandas as pd
import sys
import zipfile

from typing import List, Optional, Tuple, Union

from PyQt5.QtCore import (
	pyqtSignal, QDir, QRect, QTimer
)
from PyQt5.QtWidgets import (
	QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QVBoxLayout, QWidget
)

if __package__ is None or __package__ == "": 
	from DataManager.DataManager import DataManager
	from GUI.Basics.Enums.Difficulty import Difficulty
	from GUI.Basics.Enums.Group import Group
	from GUI.Basics.Enums.FilterOptions import SongType
	from GUI.Basics.Enums.SortType import SortType
	from GUI.Dialog import centerDialog
	from GUI.Dialog import MessageObject, ProgressObject, UpdateController
	from GUI.DifficultyButton import DifficultyButtonSet
	from GUI.FilterDialog import FilterButton
	from GUI.GroupButton import GroupButtonSet
	from GUI.MusicList import DisplayCard, MusicListWidget
	from GUI.RandomDialog import RandomWidget
	from GUI.SearchBox import SearchBox
	from GUI.SortTypeBox import SortTypeBox
else: 
	from .DataManager.DataManager import DataManager
	from .GUI.Basics.Enums.Difficulty import Difficulty
	from .GUI.Basics.Enums.Group import Group
	from .GUI.Basics.Enums.FilterOptions import SongType
	from .GUI.Basics.Enums.SortType import SortType
	from .GUI.Dialog import centerDialog
	from .GUI.Dialog import MessageObject, ProgressObject, UpdateController
	from .GUI.DifficultyButton import DifficultyButtonSet
	from .GUI.FilterDialog import FilterButton
	from .GUI.GroupButton import GroupButtonSet
	from .GUI.MusicList import DisplayCard, MusicListWidget
	from .GUI.RandomDialog import RandomWidget
	from .GUI.SearchBox import SearchBox
	from .GUI.SortTypeBox import SortTypeBox

class MainWindow(QMainWindow): 

	width_percentage = 0.7
	height_precentage = 0.8

	group_percentage = 0.1
	search_box_height_percentage = 0.025
	music_list_widget_height_percentage = 0.93
	filter_size_percentage = 0.05
	sort_type_box_height_percentage = 0.025
	diff_button_size_percentage = 0.07
	random_height_percentage = 0.07
	update_done = pyqtSignal()

	def __init__(self, available_geometry: QRect, 
			project_base_dir: str, 
			data_dir: str, buildin_dir: str, 
			resource_dir: str, parent: Optional[QWidget]=None
		): 
		super().__init__(parent)
		self.setWindowTitle("Score Record Tool")
		self.resize(
			int(available_geometry.width() * self.width_percentage), 
			int(available_geometry.height() * self.height_precentage)
		)
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

		main_widget = QWidget(self)
		self.left_layout = QVBoxLayout()
		self.middle_layout = QVBoxLayout()
		self.right_layout = QVBoxLayout()
		self.rightup_layout = QHBoxLayout()
		self.rightmiddle_layout = QVBoxLayout()
		self.rightdown_layout = QHBoxLayout()
		self.my_layout = QHBoxLayout(main_widget)
		self.setCentralWidget(main_widget)

		self.group_button_set = GroupButtonSet(int(self.group_percentage * self.width()), 
			self.data_manager.logo_array, self.data_manager.config["group"], 
			checked_group=self._init_config.get("group", 0), parent=self
		)
		self.left_layout.addWidget(self.group_button_set)

		self.search_box = SearchBox(
			int(self.search_box_height_percentage * self.height()), 
			self._init_config.get("search", ""), self
		)
		self.music_list_widget = MusicListWidget(int(self.height() * self.music_list_widget_height_percentage), self)

		self.middle_layout.addWidget(self.search_box)
		self.middle_layout.addWidget(self.music_list_widget)

		self.filter_button = FilterButton(
			self._init_config.get("filter", {}), int(self.height() * self.filter_size_percentage), self
		)
		self.sort_type_box = SortTypeBox(int(self.height() * self.sort_type_box_height_percentage), self._init_config.get("sort_type", ""), self)
		self.rightup_layout.addWidget(self.filter_button)
		self.rightup_layout.addWidget(self.sort_type_box)

		self.display_card = DisplayCard(
			self.music_list_widget.small_height, self.music_list_widget.large_height, self.height(),
			"", "", "", None, self
		)
		self.diff_button_set = DifficultyButtonSet(
			int(self.height() * self.diff_button_size_percentage), (None, None, None, None, None, None), 
			self.data_manager.config["button"], self
		)
		self.rightmiddle_layout.addWidget(self.display_card)
		self.rightmiddle_layout.addWidget(self.diff_button_set)

		self.random_widget = RandomWidget(
			int(self.height() * self.random_height_percentage), 
			self.data_manager.loadBinaryArray, self._init_config.get("random", {}), self
		)
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
		self.music_list_widget.music_updated.connect(self.refreshCurrentIndex)
		self.filter_button.filter_option_changed.connect(self.refresh)
		self.sort_type_box.currentIndexChanged.connect(self.refresh)
		self.diff_button_set.button_group.buttonClicked.connect(self.refresh)
		self.random_widget.random_button.clicked.connect(self.randomRolling)

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

	def _filterByFilterOptions(self, music_list: pd.DataFrame, filter_option: SongType) -> pd.DataFrame: 
		match filter_option: 
			case SongType.ALL: 
				pass
			case SongType.COMMISSIONED: 
				music_list = music_list[(music_list["seq"] // 100000).isin((17, 21, 22, 23, 24, 25, 26, 27))]
			case SongType.HAS_APPEND: 
				music_table = self.data_manager.music_table
				assert music_table is not None
				music_ids = music_table[music_table["musicDifficulty"] == "append"]["id_musics"].unique()
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

	def _filtering(self, 
			group: Union[Group, str], difficulty: Difficulty, filter_option: SongType, 
			search_content: str, sort_type: SortType
		) -> pd.DataFrame: 
		music_table: Optional[pd.DataFrame] = self.data_manager.music_table
		assert music_table is not None
		music_list: pd.DataFrame = music_table.copy()
		music_list: pd.DataFrame = music_list[music_list["musicDifficulty"] == difficulty.value.lower()]
		if isinstance(group, Group): 
			music_list = self._filterByUnit(music_list, group)
		elif isinstance(group, str): 
			music_list = self._filterByCustomGroup(music_list, group)
		music_list = self._filterByFilterOptions(music_list, filter_option)
		music_list = self._filterBySearchContent(music_list, search_content)

		sort_tuple = ("seq", "publishedAt", "pronunciation", "playLevel")
		sort_labels = [sort_tuple[sort_type.toIndex()], "seq"]
		sort_labels = list(dict.fromkeys(sort_labels))
		music_list = music_list.sort_values(by=sort_labels, ascending=True)

		return music_list


	def _getMusicLevels(self, music_id: int) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]]: 
		music_table = self.data_manager.music_table
		assert music_table is not None
		diff_list: pd.DataFrame = music_table.copy()
		diff_list = diff_list[diff_list["id_musics"] == music_id].set_index("musicDifficulty")
		diffs = ("easy", "normal", "hard", "expert", "master", "append")
		difficulties = tuple(diff_list.loc[diff, "playLevel"] if diff in diff_list.index else None for diff in diffs)
		return difficulties # type: ignore

	def refreshCurrentIndex(self, music_id: int) -> None: 
		difficulty = self.diff_button_set.getDifficulty()
		if len(self.music_list_widget.getCurrentMusicList()) == 0: 
			difficulties = (None, None, None, None, None, None)
		else: 
			difficulties = self._getMusicLevels(music_id)
		self.diff_button_set.setLevels((None, None, None, None, None, None), difficulty)
		self.diff_button_set.setLevels(difficulties, difficulty)
		self.music_list_widget.updateDisplayCard(difficulty, self.display_card)
		self.display_card.pause()
		self.display_card.resume()
		self._saveConfig()

	def refresh(self) -> None: 
		sort_type = self.sort_type_box.getCurrentSortType()
		group = self.group_button_set.getCurrentGroup()
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

		difficulties = self._getMusicLevels(music_id)
		vocal_list = self.data_manager.vocal_table
		assert vocal_list is not None

		self.music_list_widget.switchList(
			sort_type, group, difficulty, search_content, filter_options, 
			music_list, vocal_list, self.data_manager.config["button"][difficulty.value.lower()]["pressed"], 
			self.data_manager.getCoverArray, music_id
		)
		self.diff_button_set.setLevels((None, None, None, None, None, None), difficulty)
		self.diff_button_set.setLevels(difficulties, difficulty)
		self.music_list_widget.updateDisplayCard(difficulty, self.display_card)
		self.filter_button.setNormalState(search_content, filter_options)
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
			group = self.group_button_set.getCurrentGroup()
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

		music_list = music_list[(music_list["playLevel"] >= level_range[0]) & (music_list["playLevel"] <= level_range[1])]
		music_list.reset_index(drop=True, inplace=True)

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
		self.config["group"] = self.group_button_set.getCurrentGroupConfig()
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

