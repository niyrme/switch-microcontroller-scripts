import logging

import numpy

from lib import Button
from lib import COLOR_BLACK
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.L_UP, 0.3)

		logging.debug("wait for flash (BLACK)")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_BLACK, 5)
		self.waitAndRender(10.5)

		self.press(Button.BUTTON_A)
		self.waitAndRender(10)

		return (e + 1, self.checkShinyDialog(e, 1))
