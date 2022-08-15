import logging

import numpy

import lib
from lib import Button
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)
		self.waitAndRender(1.5)
		if not self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE):
			raise lib.ExecLock

		self.waitAndRender(0.5)

		logging.debug("waiting for dialog")

		return (e + 1, self.checkShinyDialog(e, 1.5))
