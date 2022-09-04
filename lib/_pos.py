from typing import NamedTuple


class Pos(NamedTuple):
	x: int
	y: int

	def __str__(self) -> str:
		return f"({self.x}, {self.y})"


LOADING_SCREEN_POS = Pos(705, 15)
