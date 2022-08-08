import logging

import numpy

from lib import Button
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import Gen4Script
from lib.pokemon.bdsp import SHORT_DIALOG_POS


class Script(Gen4Script):
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.L_UP, 0.3)

		logging.debug("pre-flash 1")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_BLACK, 5)
		logging.debug("post-flash 1")
		self.waitAndRender(5)

		logging.debug("waiting for dialog")
		self.awaitPixel(SHORT_DIALOG_POS, COLOR_WHITE)
		self.waitAndRender(2)

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)
		logging.debug("pre-flash 2")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		logging.debug("post-flash 2")

		logging.debug("pre-flash 3")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		logging.debug("post-flash 3")

		logging.debug("pre-flash 4")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		logging.debug("post-flash 4")

		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
		return (e + 1, rc, encounterFrame)
