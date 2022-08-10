import logging

import numpy

from lib import Button
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib import RunCrash
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import SHORT_DIALOG_POS


class Script(BDSPScript):
	def awaitInGame(self) -> None:
		self.awaitPixel(LOADING_SCREEN_POS, COLOR_BLACK)
		logging.debug("startup screen")

		self.whilePixel(LOADING_SCREEN_POS, COLOR_BLACK, 0.5, lambda: self.press(Button.BUTTON_A))
		logging.debug("after startup")

		self.waitAndRender(1)

		frame = self.getframe()
		if numpy.array_equal(frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x], (41, 41, 41)):
			raise RunCrash

		self.press(Button.BUTTON_A)
		self.waitAndRender(3)

		# loading screen to game
		if not self.awaitPixel(LOADING_SCREEN_POS, COLOR_BLACK):
			raise RunCrash
		logging.debug("loading screen")
		if not self.awaitNotPixel(SHORT_DIALOG_POS, COLOR_BLACK):
			raise RunCrash

		logging.debug("in game")
		self.waitAndRender(1)

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.waitAndRender(2)

		self.press(Button.BUTTON_A)
		self.awaitPixel(SHORT_DIALOG_POS, COLOR_WHITE)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)

		self.waitAndRender(3)
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)

		logging.debug("waiting for dialog")

		rc, encounterFrame = self.checkShinyDialog(1.5)
		return (e + 1, rc, encounterFrame)
