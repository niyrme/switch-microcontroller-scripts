import logging

import numpy

from lib import Button
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import Gen4Script


class Script(Gen4Script):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		raise NotImplementedError("Regigigas script is currently only a placeholder for the real thing later on")

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		raise NotImplementedError("Regigigas script is currently only a placeholder for the real thing later on")

		self.resetGame()
		self.awaitInGame()

		# FIXME: make not bad
		for _ in range(10):
			self.press(Button.BUTTON_A)
			self.waitAndRender(0.5)

		self.waitAndRender(3)
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)

		logging.debug("waiting for dialog")
		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
		return (e + 1, rc, encounterFrame)
