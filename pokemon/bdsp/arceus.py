import logging

import numpy

from lib import Button
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import Gen4Script


class Script(Gen4Script):
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.L_UP, 0.3)

		logging.debug("wait for flash (BLACK)")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_BLACK, 5)
		self.waitAndRender(10.5)

		self.press(Button.BUTTON_A)
		self.waitAndRender(10)

		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)

		return (e + 1, rc, encounterFrame)
