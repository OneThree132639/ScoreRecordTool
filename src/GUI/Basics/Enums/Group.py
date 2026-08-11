from enum import Enum

class Group(Enum): 

	ALL = 0
	VS = 1
	LN = 2
	MMJ = 3
	VBS = 4
	WS = 5
	NG = 6
	OTHER = 7

	@classmethod
	def fromInt(cls, value: int) -> "Group": 
		for group in cls: 
			if group.value == value: 
				return group
		raise ValueError(f"No Group with value {value}")
