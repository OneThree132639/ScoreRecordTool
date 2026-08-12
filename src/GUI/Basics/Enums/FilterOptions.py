from enum import Enum

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