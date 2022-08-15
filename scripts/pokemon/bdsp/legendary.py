import numpy

from lib import Button
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Dialga/Palkia",)

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		# walk towards legendary
		self.press(Button.L_UP, duration=0.5)
		self.waitAndRender(2)
		self.press(Button.BUTTON_B)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_B)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_B)

		# flash to enter battle
		self.awaitPixel(LOADING_SCREEN_POS, COLOR_WHITE)
		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)

		# flash inside battle
		self.awaitPixel(LOADING_SCREEN_POS, COLOR_WHITE)
		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)

		# encounter dialog
		return (e + 1, self.checkShinyDialog(e, 1.5))
