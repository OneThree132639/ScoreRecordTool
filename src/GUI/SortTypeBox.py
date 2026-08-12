from typing import Optional

from PyQt5.QtWidgets import (
	QComboBox, QWidget
)

if __package__ is None or __package__ == "": 
	from Basics.Enums.SortType import SortType
else: 
	from .Basics.Enums.SortType import SortType

class SortTypeBox(QComboBox): 

	def __init__(self, default: str="デフォルト", parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)

		self.setEditable(False)

		self.addItems(["デフォルト", "配信順", "50音順", "楽曲Lv.順"])
		self.setCurrentText(default)

	def getCurrentSortType(self) -> SortType: 
		return SortType.fromStr(self.currentText())

	def setCurrentSortType(self, sort_type: SortType) -> None: 
		self.setCurrentText(sort_type.value)
		