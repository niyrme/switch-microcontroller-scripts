from typing import final

import numpy

from ._color import Color
from ._pos import Pos


@final
class Frame:
	def __init__(self, frame: numpy.ndarray) -> None:
		self._frame = frame

	@property
	def ndarray(self) -> numpy.ndarray:
		return self._frame

	def colorAt(self, pos: Pos) -> Color:
		b, g, r = self._frame[pos.y][pos.x]
		return Color(r, g, b)
