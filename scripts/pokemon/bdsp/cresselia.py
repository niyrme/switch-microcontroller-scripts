from typing import Optional

import numpy

from lib import Button
from lib import Color
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import SHORT_DIALOG_POS


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return (
			"Stand in front of cresselia",
			"Map app active in poketch",
			"Repel in first slot in bag",
			"First pokemon in party Level < 50 but > 10 (to only encounter cresselia with repel)",
			"X menu",
			"   Map tile at (2, 1)",
			"   Bag tile at (1, 3)",
		)

	@property
	def target(self) -> str:
		return "Cresselia"

	def getName(self) -> Optional[str]:
		return "Cresselia"

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.awaitFlash(LOADING_SCREEN_POS, Color.Black(), 5)
		self.waitAndRender(1)
		self.awaitColor(SHORT_DIALOG_POS, Color.White())

		self.waitAndRender(1)
		self.press(Button.BUTTON_A)
		self.waitAndRender(1)
		self.press(Button.BUTTON_A)

		self.awaitFlash(LOADING_SCREEN_POS, Color.Black())

		self.waitAndRender(1)

		self._ser.write(b"s")
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())
		self.press(Button.EMPTY)

		return (e + 1, self.resetRoamer(e))
