import time
from itertools import cycle
from typing import Literal

import cv2
import numpy
import serial

from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import Config
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import ReturnCode
from lib.gen4 import ENCOUNTER_DIALOG_POS
from lib.gen4 import Gen4Script
from lib.gen4 import OWN_POKEMON_POS


class RandomScript(Gen4Script):
	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		super().__init__(ser, vid, config, **kwargs, windowName="Pokermans: Random")

		direction: Literal["h", "v"] = kwargs["direction"]
		assert direction in ("h", "v")

		self.directions = cycle(
			("a", "d")
			if direction == "h"
			else ("w", "s"),
		)

		self.delay = float(kwargs.get("delay"))

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		tEnd = time.time()
		frame = self.getframe()

		while not numpy.array_equal(
			frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x],
			COLOR_WHITE.tpl,
		):
			if time.time() > tEnd:
				self._ser.write(next(self.directions).encode())
				tEnd = time.time() + self.delay
			frame = self.getframe()
		print("encounter!", PAD)
		self._ser.write(b"0")

		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)

		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)

		if rc == ReturnCode.SHINY:
			return (0, ReturnCode.SHINY, encounterFrame)

		self.whileNotPixel(OWN_POKEMON_POS, COLOR_WHITE, 0.5, lambda: self.press("B"))
		self.waitAndRender(1)

		while True:
			self.press("w")
			self.waitAndRender(0.5)
			self.press("A")
			self.waitAndRender(0.5)
			self.press("B")

			if self.awaitPixel(OWN_POKEMON_POS, COLOR_BLACK, timeout=10):
				print("fade out", PAD)
				break
			else:
				self.waitAndRender(15)

		self.awaitNotPixel(OWN_POKEMON_POS, COLOR_BLACK)
		print("return to game", PAD)
		self.waitAndRender(0.5)

		return (e + 1, ReturnCode.OK, encounterFrame)
