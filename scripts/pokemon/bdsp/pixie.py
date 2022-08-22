import numpy

from lib import Button
from lib import Color
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Azelf/Uxie",)

	@property
	def target(self) -> str:
		return "Azelf/Uxie"

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)
		self.press(Button.BUTTON_A)
		self.waitAndRender(2.5)

		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		# encounter dialog
		return (e + 1, self.checkShinyDialog(e, 1.5))
