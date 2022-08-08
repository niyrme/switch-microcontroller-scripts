import numpy

from lib import Button
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.pokemon.bdsp import Gen4Script
from lib.pokemon.bdsp import SHORT_DIALOG_POS


class Script(Gen4Script):
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_BLACK, 5)
		self.waitAndRender(1)
		self.awaitPixel(SHORT_DIALOG_POS, COLOR_WHITE)

		self.waitAndRender(1)
		self.press(Button.BUTTON_A)
		self.waitAndRender(1)
		self.press(Button.BUTTON_A)

		self.awaitFlash(LOADING_SCREEN_POS, COLOR_BLACK)

		self.waitAndRender(1)

		self._ser.write(b"s")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		self.press(Button.EMPTY)

		rc, encounterFrame = self.resetRoamer()
		return (e + 1, rc, encounterFrame)