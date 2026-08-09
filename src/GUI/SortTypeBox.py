from typing import Optional

from PyQt5.QtWidgets import (
	QComboBox, QWidget
)

class SortTypeBox(QComboBox): 

	def __init__(self, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)

		self.setEditable(False)

		self.addItems(["デフォルト", "配信順", "50音順", "楽曲Lv.順"])
		self.setCurrentIndex(0)
		