from typing import Final
from typing import final
from typing import NamedTuple


@final
class Pos(NamedTuple):
	x: int
	y: int

	def __str__(self) -> str:
		return f"({self.x}, {self.y})"


LOADING_SCREEN_POS: Final[Pos] = Pos(705, 15)
