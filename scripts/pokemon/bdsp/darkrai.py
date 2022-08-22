import logging

import numpy

from lib import Button
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import SHORT_DIALOG_POS


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Darkrai",)

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.awaitColor(SHORT_DIALOG_POS, COLOR_WHITE)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)

		self.awaitNearColor(LOADING_SCREEN_POS, COLOR_WHITE, 80)
		self.awaitNotNearColor(LOADING_SCREEN_POS, COLOR_WHITE, 80)
		self.waitAndRender(2)

		logging.debug("waiting for dialog")

		return (e + 1, self.checkShinyDialog(e, 1.5))
