import cv2
import numpy
import serial

from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.gen4 import Gen4Script
from lib.gen4 import SHORT_DIALOG_POS


class CresseliaScript(Gen4Script):
	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, **kwargs) -> None:
		super().__init__(ser, vid, **kwargs, windowName="Pokermans: Cresselia")

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
		# skip collecting lunar feather

		# self.press("w", 0.5)

		# self.press("A")
		# while True:
		# 	self.waitAndRender(1)
		# 	frame = self.getframe()
		# 	if numpy.array_equal(
		# 		frame[SHORT_DIALOG_POS.y][SHORT_DIALOG_POS.x],
		# 		COLOR_WHITE.tpl
		# 	):
		# 		self.press("A")
		# 	else:
		# 		break

		self._ser.write(b"s")
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		self.press("0")

		rc, encounterFrame = self.resetRoamer()
		return (e + 1, rc, encounterFrame)
