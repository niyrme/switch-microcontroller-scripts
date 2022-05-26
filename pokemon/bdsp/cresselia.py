import cv2
import numpy
import serial

from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import Config
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.pokemon.bdsp import Gen4Script
from lib.pokemon.bdsp import SHORT_DIALOG_POS


class Script(Gen4Script):
	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		super().__init__(ser, vid, config, **kwargs, windowName="Pokermans: Cresselia")

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGameSpam()

		self.press("A")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_BLACK, 5)
		self.waitAndRender(1)
		self.awaitPixel(SHORT_DIALOG_POS, COLOR_WHITE)

		self.waitAndRender(1)
		self.press("A")
		self.waitAndRender(1)
		self.press("A")

		self.awaitFlash(LOADING_SCREEN_POS, COLOR_BLACK)

		self.waitAndRender(1)

		self._ser.write(b"s")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		self.press("0")

		rc, encounterFrame = self.resetRoamer()
		return (e + 1, rc, encounterFrame)
