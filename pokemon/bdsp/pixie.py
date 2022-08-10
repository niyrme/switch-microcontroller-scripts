import numpy

from lib import Button
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)
		self.press(Button.BUTTON_A)
		self.waitAndRender(2.5)

		self.awaitPixel(LOADING_SCREEN_POS, COLOR_WHITE)
		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)

		# encounter dialog
		rc, encounterFrame = self.checkShinyDialog(1.5)
		return (e + 1, rc, encounterFrame)
