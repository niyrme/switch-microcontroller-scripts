import logging
from typing import Optional

import numpy

from lib import Button
from lib import Color
from lib import ExecCrash
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import SHORT_DIALOG_POS


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Heatran",)

	@property
	def target(self) -> str:
		return "Heatran"

	def getName(self) -> Optional[str]:
		return "Heatran"

	def awaitInGame(self) -> None:
		self.awaitColor(LOADING_SCREEN_POS, Color.Black())
		logging.debug("startup screen")

		self.whileColor(LOADING_SCREEN_POS, Color.Black(), 0.5, lambda: self.press(Button.BUTTON_A))
		logging.debug("after startup")

		self.waitAndRender(1)

		frame = self.getframe()
		if numpy.array_equal(frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x], (41, 41, 41)):
			raise ExecCrash

		self.press(Button.BUTTON_A)
		self.waitAndRender(3)

		# loading screen to game
		self.awaitFlash(LOADING_SCREEN_POS, Color.Black())

		logging.debug("in game")
		self.waitAndRender(1)

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.waitAndRender(2)

		self.press(Button.BUTTON_A)
		self.awaitColor(SHORT_DIALOG_POS, Color.White())
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)

		self.waitAndRender(3)
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		logging.debug("waiting for dialog")

		return (e + 1, self.checkShinyDialog(e, 1.5))
