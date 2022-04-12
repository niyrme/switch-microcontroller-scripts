import time
from abc import abstractmethod
from itertools import cycle

import numpy

from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import Pixel
from lib import Pos
from lib import ReturnCode
from lib import RunCrash
from lib import Script


ENCOUNTER_DIALOG_POS = Pos(670, 430)
SHORT_DIALOG_POS = Pos(560, 455)
OWN_POKEMON_POS = Pos(5, 425)
ROAMER_MAP_POS = Pos(340, 280)
ROAMER_MAP_COLOR = Pixel(32, 60, 28)


class Gen4Script(Script):
	@abstractmethod
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		raise NotImplementedError

	def awaitInGame(self) -> None:
		crashed = not self.awaitPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("startup screen", PAD)

		crashed |= not self.awaitNotPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("after startup", PAD)

		if crashed is True:
			raise RunCrash

		# in splash screen
		self.waitAndRender(1)
		self.press("A")
		self.waitAndRender(3)
		self.press("A")
		self.waitAndRender(3)

		# loading screen to game
		crashed |= not self.awaitPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("loading screen", PAD)
		crashed |= not self.awaitNotPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)

		if crashed is True:
			raise RunCrash

		print("in game", PAD)
		self.waitAndRender(1)

	def awaitInGameSpam(self) -> None:
		self.awaitPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("startup screen", PAD)

		self.whilePixel(LOADING_SCREEN_POS, COLOR_BLACK, 0.5, lambda: self.press("A"))
		print("after startup", PAD)

		self.waitAndRender(1)

		frame = self.getframe()
		if numpy.array_equal(frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x], (41, 41, 41)):
			raise RunCrash

		self.press("A")
		self.waitAndRender(3)

		# loading screen to game
		crashed = not self.awaitPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("loading screen", PAD)
		crashed |= not self.awaitNotPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)

		if crashed is True:
			raise RunCrash

		print("in game", PAD)
		self.waitAndRender(1)

	def resetRoamer(self) -> tuple[ReturnCode, numpy.ndarray]:
		print("travel to Jubilife City", PAD)
		self.waitAndRender(0.5)
		self.press("X")
		self.waitAndRender(0.5)
		self.press("+")
		self.waitAndRender(1)
		self.press("z", 3)
		self.press("e", 0.3)
		self.press("A")
		self.waitAndRender(1.5)
		self.press("A")

		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)
		self.waitAndRender(2)

		self.press("R")
		self.waitAndRender(0.2)
		print("run towards start location", PAD)
		self.press("a", 0.8)
		self.press("s", 6.5)

		areaReloads = 0
		while True:
			self.press("R")
			self.waitAndRender(1)
			encounter = self.awaitNearPixel(ROAMER_MAP_POS, ROAMER_MAP_COLOR, 45, 5)

			self.press("R")
			self.waitAndRender(1)

			if encounter is True:
				print(f"found after reloading area {areaReloads} times", PAD)
				print("roamer in area", PAD)
				self.press("w", 0.3)
				self.waitAndRender(0.1)

				print("open backpack", PAD)
				self.press("X")
				self.waitAndRender(0.5)

				self.press("w")
				self.waitAndRender(0.1)
				self.press("d")
				self.waitAndRender(0.1)
				self.press("d")
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
					if numpy.array_equal(frame[SHORT_DIALOG_POS.y][SHORT_DIALOG_POS.x], COLOR_WHITE):
						# repel used up
						for d in (2, 1, 1):
							self.waitAndRender(d)
							self.press("A")
					frame = self.getframe()

				print("encounter!", PAD)

				self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)
				return self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
			else:
				areaReloads += 1
				self.press("w", 2)
				self.press("s", 2.1)
