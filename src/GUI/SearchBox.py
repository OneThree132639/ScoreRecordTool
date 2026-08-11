from PyQt5.QtWidgets import (
	QLineEdit
)

class SearchBox(QLineEdit): 

	def __init__(self, text: str="", parent=None): 
		super().__init__(parent)
		self.setText(text)
		self.setPlaceholderText("曲名・クリエイター名から探す")