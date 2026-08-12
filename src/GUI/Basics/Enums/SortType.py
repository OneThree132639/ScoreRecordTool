from enum import Enum

class SortType(Enum): 

	DEFAULT = "デフォルト"
	RELEASE = "配信順"
	GOJUUON = "50音順"
	LEVEL = "楽曲Lv.順"

	@classmethod
	def fromStr(cls, text: str) -> "SortType": 
		for sort_type in cls: 
			if sort_type.value == text: 
				return sort_type
		raise ValueError(f"Invalid SortType string: {text}")

	def toIndex(self) -> int: 
		return list(SortType).index(self)