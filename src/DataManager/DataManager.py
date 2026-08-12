import copy
import enum
import json
import logging
import numpy as np
import os
import pandas as pd
import requests
import shutil

from filesplit.merge import Merge
from io import BytesIO
from PIL import Image
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

class DownloadStatus(enum.Enum): 
	UNMODIFIED = "unmodified"
	SUCCESS = "success"
	FAIL = "fail"

class JsonDownloadError(Exception): 
	pass

class DataManager: 

	timeout = 10 # seconds
	headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"}

	# DB stands for database
	dburls = {
		"bestDBurl": "https://raw.githubusercontent.com/Sekai-World/sekai-master-db-diff/main/{}.json", 
		"harukiDBGHurl": "https://raw.githubusercontent.com/Team-Haruki/haruki-sekai-master/refs/heads/main/master/{}.json"
	}
	picurl = {
		"sekaibest": {
			"url": "https://storage.sekai.best/sekai-jp-assets/music/jacket/jacket_s_{}/jacket_s_{}.webp", 
			"paramtype": "id", 
			"numparam": 2
		}, 
		"pjsekai": {
			"url": "https://pjsekai.com/?plugin=ref&page={}&src={}.jpg", 
			"paramtype": "title", 
			"numparam": 2
		}, 
		"sekaipedia": {
			"url": "https://www.sekaipedia.org/wiki/File:Jacket{}.png", 
			"paramtype": "id", 
			"numparam": 1
		}
	}

	cover_size = 740 # pixels

	def __init__(self, project_base_dir: str, 
			data_dir: str, buildin_dir: str, resource_dir: str, 
			choose_resource_file: Callable[[], bool]
		): 
		self.project_base_dir = project_base_dir
		self.data_dir = data_dir
		self.buildin_dir = buildin_dir
		self.resource_dir = resource_dir
		self.choose_resource_file = choose_resource_file

		self.json_dir = os.path.join(data_dir, "json")
		self.table_dir = os.path.join(data_dir, "table")
		self.cover_dir = os.path.join(data_dir, "musicCovers")
		self.binary_dir = os.path.join(data_dir, "binary")

		# data

		os.makedirs(self.json_dir, exist_ok=True)
		os.makedirs(self.table_dir, exist_ok=True)
		os.makedirs(self.cover_dir, exist_ok=True)
		os.makedirs(self.binary_dir, exist_ok=True)
		self.last_modified = self.loadLastModifiedJson()

		self.characterProfiles: Optional[pd.DataFrame] = None
		self.gameCharacters: Optional[pd.DataFrame] = None
		self.musicArtists: Optional[pd.DataFrame] = None
		self.musicAssetVariants: Optional[pd.DataFrame] = None
		self.musicCollaborations: Optional[pd.DataFrame] = None
		self.musicDifficulties: Optional[pd.DataFrame] = None
		self.musics: Optional[pd.DataFrame] = None
		self.musicTags: Optional[pd.DataFrame] = None
		self.musicVocals: Optional[pd.DataFrame] = None
		self.outsideCharacters: Optional[pd.DataFrame] = None

		self.cover_index_dict = {}
		self.cover_array: Optional[np.ndarray] = None
		self.loadCoverData()

		self.music_table: Optional[pd.DataFrame] = self.loadCustomTable("musicTable.csv")
		self.loadCoverArray()
		self.vocal_table: Optional[pd.DataFrame] = self.loadCustomTable("vocalTable.csv")

		self.custom_list: Dict[str, List[int]] = {}

		# build in

		self.config: Dict[str, Any] = self.loadConfig()
		self.logo_array: np.ndarray = self.loadBinaryArray("logo_array")

	def _hiraganaToKatakana(self, s: str) -> str: 
		try: 
			output = ""
			for c in s: 
				if 12353 <= ord(c) <= 12436: 
					output += chr(ord(c) + 96)
				else: 
					output += c
			return output
		except Exception as e: 
			logging.error("Error converting hiragana to katakana: %s, string: %s", e, s)
			raise e

	def loadLastModifiedJson(self) -> Dict[str, Dict[str, Dict[str, str]]]: 
		filepath = os.path.join(self.json_dir, "lastModified.json")
		if os.path.exists(filepath): 
			with open(filepath, "r", encoding='utf-8') as fL:
				jsonfile = json.load(fL)
				return jsonfile
		else: 
			return {}

	def saveLastModifiedJson(self) -> None: 
		filepath = os.path.join(self.json_dir, "lastModified.json")
		with open(filepath, "w", encoding='utf-8') as fL:
			json.dump(self.last_modified, fL, ensure_ascii=False, indent=4)

	def getJsonRequestHeader(self, db_name: str, dburl_key: str) -> Dict[str, str]: 
		if db_name not in self.last_modified: 
			self.last_modified[db_name] = {}
		if dburl_key not in self.last_modified[db_name]: 
			self.last_modified[db_name][dburl_key] = {}

		headers = copy.deepcopy(self.headers)
		if "ETag" in self.last_modified[db_name][dburl_key]: 
			if os.path.exists(os.path.join(self.json_dir, "{}.json".format(db_name))): 
				headers["If-None-Match"] = self.last_modified[db_name][dburl_key]["ETag"]
			else: 
				self.last_modified[db_name][dburl_key].pop("ETag", None)
		return headers

	def setLastModified(self, db_name: str, dburl_key: str, key: str, value: str) -> None: 
		if db_name not in self.last_modified: 
			self.last_modified[db_name] = {}
		if dburl_key not in self.last_modified[db_name]: 
			self.last_modified[db_name][dburl_key] = {}
		self.last_modified[db_name][dburl_key][key] = value
	
	def downloadJson(self, db_name: str) -> DownloadStatus: 
		for (key, value) in self.dburls.items(): 
			headers = self.getJsonRequestHeader(db_name, key)

			try: 
				json_response = requests.get(value.format(db_name), timeout=self.timeout, headers=headers)
			except requests.RequestException as e: 
				logging.error("Error downloading JSON data from %s: %s", key, e)
				continue

			try: 
				json_response.raise_for_status()
			except requests.HTTPError as e: 
				logging.error("HTTP error occurred while downloading JSON data from %s: %s", key, e)
				continue

			if json_response.status_code == 304: 
				return DownloadStatus.UNMODIFIED
			elif json_response.status_code == 200: 
				self.setLastModified(db_name, key, "ETag", json_response.headers["ETag"])
				logging.debug("Successfully downloaded JSON data from %s", key)

			json_data = json_response.json()
			logging.debug("Successfully downloaded JSON data from %s", key)
			with open(os.path.join(self.json_dir, "{}.json".format(db_name)), "w", encoding='utf-8') as fL:
				json.dump(json_data, fL, ensure_ascii=False, indent=4)
				logging.debug("Saved JSON data to %s", os.path.join(self.json_dir, "{}.json".format(db_name)))
			return DownloadStatus.SUCCESS
		else: 
			logging.error("Failed to download JSON data from all sources")
			return DownloadStatus.FAIL

	def convertJsonToCsv(self, db_name: str) -> None: 
		filepath = os.path.join(self.json_dir, "{}.json".format(db_name))
		if not os.path.exists(filepath): 
			logging.error("JSON file %s does not exist", filepath)
			raise FileNotFoundError("JSON file {} does not exist".format(filepath))

		df = pd.read_json(filepath)
		df.to_csv(os.path.join(self.table_dir, "{}.csv".format(db_name)), index=False)
		logging.debug("Converted JSON data to CSV: %s", os.path.join(self.table_dir, "{}.csv".format(db_name)))

	def loadCsv(self, db_name: str) -> None: 
		filepath = os.path.join(self.table_dir, "{}.csv".format(db_name))
		setattr(self, db_name, pd.read_csv(filepath)) 

	def updateCovers(self) -> Generator[Tuple[str, int, int], None, None]: 
		if not isinstance(self.musics, pd.DataFrame): 
			return
		total = len(self.musics)
		for idx, (_, row) in enumerate(self.musics.iterrows()): 
			music_id = row["id"]
			id_str = str(music_id).zfill(3)
			filepath = os.path.join(self.cover_dir, "{}.png".format(id_str))
			if music_id not in self.cover_index_dict and not os.path.exists(filepath): 
				try: 
					self.downloadCover(row["id"], row["title"])
				except Exception as e: 
					logging.error("Error when downloading cover of {}: {}".format(row["title"], e))
					continue
			yield ("Updating cover of {}...".format(row["title"]), idx, total)

	def process(self, db_name: str) -> None: 
		if not os.path.exists(os.path.join(self.table_dir, "{}.csv".format(db_name))): 
			self.last_modified.pop(db_name, None)
		status = self.downloadJson(db_name)
		if status == DownloadStatus.SUCCESS: 
			self.convertJsonToCsv(db_name)
			self.loadCsv(db_name)
		elif status == DownloadStatus.FAIL: 
			logging.warning("Failed to download JSON data, try to load local data")
			try: 
				self.loadCsv(db_name)
			except FileNotFoundError: 
				logging.warning("Failed to load local data. Please try download later. ")
		elif status == DownloadStatus.UNMODIFIED: 
			logging.debug("JSON data not modified since last download")
			self.loadCsv(db_name)

	def downloadCover(self, music_id: int, music_title: str) -> DownloadStatus: 
		id_str = str(music_id).zfill(3)
		filepath = os.path.join(self.cover_dir, "{}.png".format(id_str))
		os.makedirs(os.path.dirname(filepath), exist_ok=True)
		if os.path.exists(filepath): 
			return DownloadStatus.UNMODIFIED

		for key, value in self.picurl.items(): 
			numparam = value["numparam"]
			paramtype = value["paramtype"]
			if paramtype == "id": 
				params = [id_str] * numparam
			elif paramtype == "title": 
				params = [music_title.replace(" ", "%20")] * numparam
			else: 
				raise ValueError("Invalid paramtype: {}".format(paramtype))
			url = value["url"].format(*params)

			try: 
				cover_response = requests.get(url, timeout=self.timeout, headers=self.headers)
			except requests.RequestException as e: 
				logging.error("Error downloading cover image from %s: %s", key, e)
				continue

			try: 
				cover_response.raise_for_status()
			except requests.HTTPError as e: 
				logging.error("HTTP error occurred while downloading cover image from %s: %s", key, e)
				continue

			image = Image.open(BytesIO(cover_response.content))
			image = image.resize((self.cover_size, self.cover_size))
			if image.mode != "RGBA": 
				image = image.convert("RGBA")

			image.save(filepath, format="PNG")
			logging.debug("Successfully downloaded cover image from %s and saved to %s", key, filepath)
			return DownloadStatus.SUCCESS
		else: 
			logging.error("Failed to download cover image from all sources")
			return DownloadStatus.FAIL

	def buildMusicTable(self) -> pd.DataFrame: 
		assert self.musics is not None
		assert self.musicDifficulties is not None
		assert self.musicArtists is not None

		def apply_func(row: pd.Series, col_label: str, func: Callable[[str], str]) -> str: 
			# logging.debug("Current row: \n%s", row)
			return func(row[col_label])
		
		
		table = pd.merge(
			self.musics, self.musicDifficulties, left_on="id", right_on="musicId", how="inner", 
			suffixes=("_musics", "_musicDifficulties")
		)
		# "Asia/Shanghai" for UTC+8, "Asia/Tokyo" for UTC+9
		table["publish-date"] = pd.to_datetime(table["publishedAt"], unit="ms", utc=True).dt.tz_convert("Asia/Shanghai")
		table["pronunciationKatakana"] = table.apply(
			lambda row: apply_func(row, "pronunciation", self._hiraganaToKatakana), axis=1
		)

		table["artistsName"] = table["creatorArtistId"].map(self.musicArtists.set_index("id")["name"])
		table["artistsPronunciation"] = table["creatorArtistId"].map(self.musicArtists.set_index("id")["pronunciation"])
		table["artistsPronunciationKatakana"] = table.apply(
			lambda row: apply_func(row, "artistsPronunciation", self._hiraganaToKatakana), axis=1
		)
		# logging.debug("table columns: {}".format(table.columns))
		table.drop(columns=[
			"releaseConditionId_musics", "categories", "dancerCount", "selfDancerPosition", "assetbundleName", 
			"liveTalkBackgroundAssetbundleName", "releasedAt", "liveStageId", "fillerSec", "isNewlyWrittenMusic", 
			"musicId", "releaseConditionId_musicDifficulties"
		], inplace=True)
		return table

	def buildVocalTable(self) -> pd.DataFrame: 
		assert self.musicVocals is not None
		assert self.gameCharacters is not None
		assert self.outsideCharacters is not None

		def get_character(char_type: str, char_id: int, gChar: pd.DataFrame, oChar: pd.DataFrame) -> str: 
			if char_type == "game_character": 
				first_name = gChar.set_index("id").loc[char_id, "firstName"]
				first_name = "" if pd.isna(first_name) else first_name
				given_name = gChar.set_index("id").loc[char_id, "givenName"]
				return first_name + given_name
			elif char_type == "outside_character":
				return oChar.set_index("id").loc[char_id, "name"]
			else: 
				raise ValueError("Invalid character type: {}".format(char_type))

		def get_vocal(row: pd.Series, gChar: pd.DataFrame, oChar: pd.DataFrame) -> str: 
			characters_str: str = row["characters"]
			characters_str = characters_str.replace("\'", "\"")
			try: 
				vocal_list = json.loads(characters_str)
			except json.JSONDecodeError as e: 
				logging.error("Error decoding JSON data: %s", e)
				return row["caption"]
			if len(vocal_list) == 0: 
				return row["caption"]
			vocal_str = "Vo. " + get_character(vocal_list[0]["characterType"], vocal_list[0]["characterId"], gChar, oChar)
			for vocal in vocal_list[1:]: 
				vocal_str += "、" + get_character(vocal["characterType"], vocal["characterId"], gChar, oChar)
			return vocal_str

		table = self.musicVocals.copy()
		table["vocal"] = table.apply(get_vocal, axis=1, gChar=self.gameCharacters, oChar=self.outsideCharacters)
		return table

	def updateMusicTable(self) -> None: 
		if self.music_table is None: 
			self.music_table = self.buildMusicTable()
		else: 
			updated_table = self.buildMusicTable()
			if not self.music_table.columns.equals(updated_table.columns): 
				self.music_table = updated_table
				return
			combined = pd.concat([self.music_table, updated_table], ignore_index=True)
			self.music_table = combined.drop_duplicates(subset=["id_musics", "musicDifficulty"], keep="first")
		self.loadCoverArray()
		self.saveCoverData()

	def updateVocalTable(self) -> None: 
		if self.vocal_table is None: 
			self.vocal_table = self.buildVocalTable()
		else: 
			updated_table = self.buildVocalTable()
			if not self.vocal_table.columns.equals(updated_table.columns): 
				self.vocal_table = updated_table
				return
			combined = pd.concat([self.vocal_table, updated_table], ignore_index=True)
			self.vocal_table = combined.drop_duplicates(subset=["id"], keep="first")

	def loadCustomTable(self, table_name: str) -> Optional[pd.DataFrame]: 
		filepath = os.path.join(self.table_dir, table_name)
		if os.path.exists(filepath): 
			return pd.read_csv(filepath)
		else: 
			return None

	def loadCoverData(self) -> None: 
		array_path = os.path.join(self.binary_dir, "cover_array.npy")
		index_dict_path = os.path.join(self.binary_dir, "cover_index_dict.json")
		if not os.path.exists(array_path): 
			buildin_array_split_path = os.path.join(self.resource_dir, "binary", "cover_splits")
			outputfile_name = "cover_array.npz"
			temp_array_path = os.path.join(self.binary_dir, outputfile_name)
			buildin_index_dict_path = os.path.join(self.resource_dir, "binary", "cover_index_dict.json")
			while True: 
				try: 
					shutil.copy(buildin_index_dict_path, index_dict_path)
					merge = Merge(buildin_array_split_path, self.binary_dir, outputfile_name)
					merge.merge()
					break
				except Exception as e: 
					logging.warning("Error occurred when trying to access resource files: %s", e)
					self.choose_resource_file()	
			with np.load(temp_array_path) as data: 
				np.save(array_path, data["array"], allow_pickle=False)
			os.remove(temp_array_path)
		
		self.cover_array = np.load(array_path)
		with open(index_dict_path, "r", encoding='utf-8') as f:
			load_dict = json.load(f)
			self.cover_index_dict = {int(k): v for k, v in load_dict.items()}

	def saveCoverData(self) -> None: 
		assert self.cover_array is not None
		array_path = os.path.join(self.binary_dir, "cover_array.npy")
		index_dict_path = os.path.join(self.binary_dir, "cover_index_dict.json")
		np.save(array_path, self.cover_array)
		with open(index_dict_path, "w", encoding='utf-8') as f:
			json.dump(self.cover_index_dict, f)

	def loadCoverArray(self) -> None: 
		if self.music_table is None: 
			return

		images: List[np.ndarray] = []
		count = 0 if self.cover_array is None else self.cover_array.shape[0]
		for i, (_, row) in enumerate(self.music_table.iterrows()): 
			music_id = row["id_musics"]
			if music_id in self.cover_index_dict: 
				continue
			try: 
				image_array = np.array(self.loadCover(music_id))
				images.append(np.expand_dims(image_array, axis=0))
			except FileNotFoundError: 
				logging.warning("Cover not found for music ID: %s", music_id)
				continue
			self.cover_index_dict[music_id] = count
			count += 1
		self.cover_array = np.concatenate([self.cover_array] + images, axis=0) if self.cover_array is not None else np.stack(images)

	def loadCover(self, music_id: int) -> Image.Image: 
		filepath = os.path.join(self.cover_dir, "{}.png".format(str(music_id).zfill(3)))
		image = Image.open(filepath)
		if image.mode != "RGBA": 
			image = image.convert("RGBA")
		image.save(filepath)
		return image

	def getCoverArray(self, music_id: int) -> Optional[np.ndarray]: 
		assert self.cover_array is not None
		index = self.cover_index_dict.get(music_id, None)
		if index is None: 
			return None
		return self.cover_array[index]

	def saveCustomTable(self, table: Optional[pd.DataFrame], table_name: str) -> None: 
		if table is not None: 
			table.to_csv(os.path.join(self.table_dir, table_name), index=False)

	def loadConfig(self) -> Dict[str, Any]: 
		with open(os.path.join(self.buildin_dir, "config.json")) as f: 
			return json.load(f)

	def loadBinaryArray(self, array_name: str) -> np.ndarray: 
		while True: 
			try: 
				array_path = os.path.join(self.resource_dir, "binary", "{}.npy".format(array_name))
				break
			except Exception as e: 
				logging.warning("Failed when accessing resource file: %s", e)
				self.choose_resource_file()
		return np.load(array_path, "r")

	def loadLocalResources(self) -> None: 
		table_names = ["musicTags"]
		for table_name in table_names: 
			self.loadCsv(table_name)
	

if __name__ == "__main__": 
	data_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data"))
	log_dir = os.path.join(data_dir, "log")

	os.makedirs(log_dir, exist_ok=True)

	logging.basicConfig(
		level=logging.DEBUG, 
		format="%(asctime)s [%(levelname)s] %(message)s", 
		handlers=[
			logging.FileHandler(os.path.join(log_dir, "debug.log"), mode="w", encoding="utf-8"), 
			logging.StreamHandler()
		], 
		datefmt="%Y-%m-%d %H:%M:%S"
	)