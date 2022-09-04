from __future__ import annotations

from typing import NamedTuple


class Color(NamedTuple):
	r: int
	g: int
	b: int

	@property
	def tpl(self) -> tuple[int, int, int]:
		return (self.r, self.g, self.b)

	@staticmethod
	def White() -> Color:
		return Color(255, 255, 255)

	@staticmethod
	def Black() -> Color:
		return Color(0, 0, 0)

	def __str__(self) -> str:
		return f"({self.r}, {self.g}, {self.b})"

	def distance(self, other: Color) -> int:
		return sum(
			(c2 - c1) ** 2
			for c1, c2 in zip(self.tpl, other.tpl)
		)
