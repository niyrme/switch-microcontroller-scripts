import numpy

from lib import Button
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.pressN(Button.BUTTON_A, 8, 1.5, render=True)

		self.waitAndRender(3)
		self.press(Button.BUTTON_A)

		self.waitAndRender(3)
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		self.waitAndRender(0.3)

		return (e + 1, self.checkShinyDialog(e, 1))
