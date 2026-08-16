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

	@classmethod
	def formerDifficulty(cls, diff: "Difficulty") -> "Difficulty": 
		if diff == cls.EASY: 
			return cls.APPEND
		elif diff == cls.NORMAL: 
			return cls.EASY
		elif diff == cls.HARD: 
			return cls.NORMAL
		elif diff == cls.EXPERT: 
			return cls.HARD
		elif diff == cls.MASTER: 
			return cls.EXPERT
		elif diff == cls.APPEND: 
			return cls.MASTER
		else: 
			raise ValueError(f"Invalid difficulty: {diff}")

	@classmethod
	def latterDifficulty(cls, diff: "Difficulty") -> "Difficulty": 
		if diff == cls.APPEND: 
			return cls.EASY
		elif diff == cls.EASY: 
			return cls.NORMAL
		elif diff == cls.NORMAL: 
			return cls.HARD
		elif diff == cls.HARD: 
			return cls.EXPERT
		elif diff == cls.EXPERT: 
			return cls.MASTER
		elif diff == cls.MASTER: 
			return cls.APPEND
		else: 
			raise ValueError(f"Invalid difficulty: {diff}")

	@classmethod
	def toIndex(cls, diff: "Difficulty") -> int: 
		if diff == cls.EASY: 
			return 0
		elif diff == cls.NORMAL: 
			return 1
		elif diff == cls.HARD: 
			return 2
		elif diff == cls.EXPERT: 
			return 3
		elif diff == cls.MASTER: 
			return 4
		elif diff == cls.APPEND: 
			return 5
		else: 
			raise ValueError(f"Invalid difficulty: {diff}")

	@classmethod
	def fromIndex(cls, index: int) -> "Difficulty": 
		if index == 0: 
			return cls.EASY
		elif index == 1: 
			return cls.NORMAL
		elif index == 2: 
			return cls.HARD
		elif index == 3: 
			return cls.EXPERT
		elif index == 4: 
			return cls.MASTER
		elif index == 5: 
			return cls.APPEND
		else: 
			raise ValueError(f"Invalid difficulty index: {index}")