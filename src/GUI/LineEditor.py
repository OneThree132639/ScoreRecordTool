from PyQt5.QtCore import (
	QSize
)
from PyQt5.QtGui import (
	QFont
)
from PyQt5.QtWidgets import (
	QLineEdit
)

class SearchBox(QLineEdit): 

	def __init__(self, pixel_size: int, text: str="", parent=None): 
		super().__init__(parent)
		self.setText(text)
		self.setPlaceholderText("曲名・クリエイター名から探す")

		font = self.font()
		font.setPixelSize(pixel_size)
		self.setFont(font)

class CustomListTitleBox(QLineEdit): 

	width_height_ratio = 20

	def __init__(self, pixel_size: int, text: str="", parent=None): 
		super().__init__(parent)
		self.setText(text)
		self.setPlaceholderText("マイリストのタイトルを入力")

		font = self.font()
		font.setPixelSize(pixel_size)
		self.setFont(font)

		self.setFixedWidth(pixel_size * self.width_height_ratio)