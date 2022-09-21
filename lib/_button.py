from enum import Enum


class Button(Enum):
	EMPTY = "0"
	BUTTON_A = "A"
	BUTTON_B = "B"
	BUTTON_X = "X"
	BUTTON_Y = "Y"
	BUTTON_HOME = "H"
	BUTTON_PLUS = "+"
	BUTTON_MINUS = "-"
	BUTTON_L = "L"
	BUTTON_R = "R"
	BUTTON_ZL = "l"
	BUTTON_ZR = "r"
	L_UP_LEFT = "q"
	L_UP = "w"
	L_UP_RIGHT = "e"
	L_LEFT = "a"
	L_RIGHT = "d"
	L_DOWN_LEFT = "z"
	L_DOWN_RIGHT = "c"
	L_DOWN = "s"
	R_UP_LEFT = "y"
	R_UP = "u"
	R_UP_RIGHT = "i"
	R_LEFT = "h"
	R_RIGHT = "k"
	R_DOWN_LEFT = "n"
	R_DOWN_RIGHT = "m"
	R_DOWN = "j"

	def __str__(self) -> str:
		return self.value

	def encode(self) -> bytes:
		return str(self.value).encode()
