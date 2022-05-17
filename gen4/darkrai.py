import cv2
import numpy
import serial

from lib import COLOR_WHITE
from lib import Config
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import ReturnCode
from lib.gen4 import ENCOUNTER_DIALOG_POS
from lib.gen4 import Gen4Script
from lib.gen4 import SHORT_DIALOG_POS


class DarkraiScript(Gen4Script):
	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		super().__init__(ser, vid, config, **kwargs, windowName="Pokermans: Darkrai")

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGameSpam()

		self.press("A")
		self.awaitPixel(SHORT_DIALOG_POS, COLOR_WHITE)
		self.waitAndRender(0.5)
		self.press("A")
		self.waitAndRender(0.5)
		self.press("A")

		self.awaitNearPixel(LOADING_SCREEN_POS, COLOR_WHITE, 80)
		self.awaitNotNearPixel(LOADING_SCREEN_POS, COLOR_WHITE, 80)
		self.waitAndRender(2)

		print("waiting for dialog", PAD)

		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
		return (e + 1, rc, encounterFrame)
