from typing import Optional

import numpy

from lib import Button
from lib import Color
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Regigigas",)

	@property
	def target(self) -> str:
		return "Regigigas"

	def getName(self) -> Optional[str]:
		return "Regigigas"

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.waitAndRender(1.5)

		self.whileNotColor(LOADING_SCREEN_POS, Color.White(), 0.5, lambda: self.press(Button.BUTTON_A))

		self.waitAndRender(3)

		self.awaitFlash(LOADING_SCREEN_POS, Color.White())
		self.waitAndRender(0.3)

		return (e + 1, self.checkShinyDialog(e, 1))
