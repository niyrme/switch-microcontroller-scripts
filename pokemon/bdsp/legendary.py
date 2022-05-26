import cv2
import numpy
import serial

from lib import COLOR_WHITE
from lib import Config
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import Gen4Script


class Script(Gen4Script):
	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		super().__init__(ser, vid, config, **kwargs, windowName="Pokermans: Legendary")

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGameSpam()

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
