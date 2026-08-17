from enum import Enum, IntFlag
from enum import auto
from typing import Dict

class SongType(Enum): 

	ALL = "すべて"
	COMMISSIONED = "書き下ろし楽曲"
	HAS_APPEND = "APPENDあり"

	@classmethod
	def fromStr(cls, value: str) -> "SongType": 
		for member in cls: 
			if member.value == value: 
				return member
		raise ValueError(f"{value} is not a valid {cls.__name__}")

class Timeline(IntFlag):

	NONE = 0
	SERVICE_END = auto()
	PLAYABLE = auto()
	UNPUBLISHED = auto()

	@classmethod
	def fromStr(cls, value: str) -> "Timeline": 
		map_dict = {
			"サービス終了": cls.SERVICE_END, 
			"プレイ可能": cls.PLAYABLE, 
			"未公開": cls.UNPUBLISHED
		}
		if value in map_dict: 
			return map_dict[value]
		raise ValueError(f"{value} is not a valid {cls.__name__}")

	@classmethod
	def toStr(cls, value: "Timeline") -> str: 
		map_dict = {
			cls.SERVICE_END: "サービス終了", 
			cls.PLAYABLE: "プレイ可能", 
			cls.UNPUBLISHED: "未公開"
		}
		if value in map_dict: 
			return map_dict[value]
		raise ValueError(f"{value} is not a valid {cls.__name__}")

	@classmethod
	def fromStrList(cls, values: list[str]) -> "Timeline": 
		result = cls.NONE
		for value in values: 
			result |= cls.fromStr(value)
		return result

	@classmethod
	def toStrList(cls, value: "Timeline") -> list[str]: 
		result = []
		for i in cls: 
			if value & i: 
				result.append(cls.toStr(i))
		return result