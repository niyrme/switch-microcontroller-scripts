import logging

import numpy

from lib import Button
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import Gen4Script
from lib.pokemon.bdsp import OWN_POKEMON_POS


class Script(Gen4Script):
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.press(Button.BUTTON_A)
		self.waitAndRender(3)
		self.press(Button.BUTTON_A)
		self.waitAndRender(2.5)

		self.awaitPixel(LOADING_SCREEN_POS, COLOR_WHITE)
		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)

		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
		if rc == ReturnCode.SHINY:
			return (e + 1, ReturnCode.SHINY, encounterFrame)

		self.whileNotPixel(OWN_POKEMON_POS, COLOR_WHITE, 0.5, lambda: self.press(Button.BUTTON_B))
		self.waitAndRender(1)

		self.runFromEncounter()

		self.press(Button.BUTTON_A)
		self.waitAndRender(0.5)

		logging.debug("reload area")
		self.press(Button.L_DOWN, 3.5)
		self.press(Button.L_UP, 3.8)
		return (e + 1, ReturnCode.OK, encounterFrame)
