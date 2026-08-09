from enum import Enum

class Difficulty(Enum): 
	EASY = "Easy"
	NORMAL = "Normal"
	HARD = "Hard"
	EXPERT = "Expert"
	MASTER = "Master"
	APPEND = "Append"

	@classmethod
	def fromStr(cls, diff_str: str) -> "Difficulty": 
		diff_str = diff_str.lower()
		if diff_str == "easy": 
			return cls.EASY
		elif diff_str == "normal": 
			return cls.NORMAL
		elif diff_str == "hard": 
			return cls.HARD
		elif diff_str == "expert": 
			return cls.EXPERT
		elif diff_str == "master": 
			return cls.MASTER
		elif diff_str == "append": 
			return cls.APPEND
		else: 
			raise ValueError(f"Invalid difficulty string: {diff_str}")