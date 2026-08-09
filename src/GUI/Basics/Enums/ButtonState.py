from enum import Enum

class ButtonState(Enum): 
	NORMAL = "normal"
	HOVER = "hover"
	PRESSED = "pressed"
	DISABLED = "disabled"
	DISABLED_PRESSED = "disabled_pressed"