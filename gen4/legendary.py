import numpy

from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib import Script
from lib.gen4 import awaitInGameSpam
from lib.gen4 import ENCOUNTER_DIALOG_POS


class LegendaryScript(Script):
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		awaitInGameSpam(self._ser, self._vid)

		# walk towards legendary
		self.press("w", duration=0.5)
		self.waitAndRender(2)
		self.press("B")
		self.waitAndRender(0.5)
		self.press("B")
		self.waitAndRender(0.5)
		self.press("B")

		# flash to enter battle
		self.awaitPixel(LOADING_SCREEN_POS, COLOR_WHITE)
		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)

		# flash inside battle
		self.awaitPixel(LOADING_SCREEN_POS, COLOR_WHITE)
		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)

		# encounter dialog
		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
		return (e + 1, rc, encounterFrame)
