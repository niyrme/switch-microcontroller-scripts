import time
from itertools import cycle

import cv2
import numpy
import serial

from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import Pixel
from lib import Pos
from lib import ReturnCode
from lib.gen4 import ENCOUNTER_DIALOG_POS
from lib.gen4 import Gen4Script
from lib.gen4 import SHORT_DIALOG_POS


ROAMER_MAP_POS = Pos(340, 280)
ROAMER_MAP_COLOR = Pixel(32, 60, 28)
ROAMER_NOT_MAP_COLOR = Pixel(72, 132, 64)


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

		print("travel to Jubilife City", PAD)
		self.waitAndRender(0.5)
		self.press("X")
		self.waitAndRender(0.5)
		self.press("+")
		self.waitAndRender(1)
		self.press("s", 0.75)
		self.waitAndRender(0.3)
		self.press("d", 0.1)
		self.waitAndRender(0.5)
		self.press("A")
		self.waitAndRender(1.5)
		self.press("A")

		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		self.waitAndRender(2)

		self.press("R")
		self.waitAndRender(0.2)
		print("run towards start location", PAD)
		self.press("d", 1)
		self.press("a", 1.4)
		self.press("s", 6.5)

		while True:
			self.press("R")
			self.waitAndRender(1)
			encounter = self.awaitNearPixel(ROAMER_MAP_POS, ROAMER_MAP_COLOR, 45, 5)

			self.press("R")
			self.waitAndRender(1)

			if encounter is True:
				print("roamer in area", PAD)
				self.press("w", 0.3)
				self.waitAndRender(0.1)

				print("open backpack", PAD)
				self.press("X")
				self.waitAndRender(0.5)

				for b in ("w", "d", "d"):
					self.press(b)
					self.waitAndRender(0.1)

				self.press("A")
				self.waitAndRender(1.5)

				for _ in range(4):
					self.press("d")
					self.waitAndRender(0.1)

				print("use repel", PAD)
				self.press("A")
				self.waitAndRender(1)
				self.press("A")
				self.waitAndRender(1)
				self.press("A")
				for _ in range(4):
					self.waitAndRender(1)
					self.press("B")

				self._ser.write(b"a")

				_directions = cycle(("a", "d"))
				print("go for encounter", PAD)
				tEnd = time.time() + 2.5
				frame = self.getframe()
				while not numpy.array_equal(
					frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x],
					COLOR_WHITE.tpl,
				):
					if time.time() > tEnd:
						self._ser.write(next(_directions).encode())
						tEnd = time.time() + 0.5
					frame = self.getframe()

				print("encounter!", PAD)

				self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)
				rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)

				return (e + 1, rc, encounterFrame)
			else:
				print(f"not here{PAD}\r", end="")
				self.press("w", 2.5)
				self.press("s", 2.6)
