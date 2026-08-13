from PyQt5.QtCore import (
	Qt
)
from PyQt5.QtGui import (
	QFont
)

def strToFontWeight(font_weight: str) -> QFont.Weight: 
	match font_weight: 
		case "thin": 
			return QFont.Weight.Thin
		case "extra-light": 
			return QFont.Weight.ExtraLight
		case "light": 
			return QFont.Weight.Light
		case "normal": 
			return QFont.Weight.Normal
		case "medium": 
			return QFont.Weight.Medium
		case "demi-bold": 
			return QFont.Weight.DemiBold 
		case "bold": 
			return QFont.Weight.Bold
		case "extra-bold": 
			return QFont.Weight.ExtraBold
		case "black": 
			return QFont.Weight.Black
		case _: 
			raise ValueError("Invalid font weight")

def strToFontStyle(font_style: str) -> QFont.Style: 
	match font_style: 
		case "normal": 
			return QFont.Style.StyleNormal
		case "italic": 
			return QFont.Style.StyleItalic
		case "oblique": 
			return QFont.Style.StyleOblique
		case _: 
			raise ValueError("Invalid font style")

