import logging
from typing import Optional

import numpy

from lib import Button
from lib import Color
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Giratina",)

	@property
	def target(self) -> str:
		return "Giratina"

	def getName(self) -> Optional[str]:
		return "Giratina"

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)
		self.waitAndRender(1.5)
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		self.waitAndRender(0.5)

		logging.debug("waiting for dialog")

		return (e + 1, self.checkShinyDialog(e, 1.5))
