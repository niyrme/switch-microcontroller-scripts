import numpy

from lib import Button
from lib import Color
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import Pos
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Regigigas",)

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.waitAndRender(1.5)

		self.whileNearColor(Pos(705, 424), Color(186, 246, 255), 12, 0.5, lambda: self.press(Button.BUTTON_A))

		self.waitAndRender(3)
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		self.waitAndRender(0.3)

		return (e + 1, self.checkShinyDialog(e, 1))
