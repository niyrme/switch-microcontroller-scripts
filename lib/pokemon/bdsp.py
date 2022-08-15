import argparse
import difflib
import logging
import pathlib
import time
from abc import abstractmethod
from itertools import cycle
from typing import Optional

import cv2
import numpy
import pytesseract
import serial

from . import ExecShiny
from . import LOG_DELAY
from lib import Button
from lib import Capture
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import Config
from lib import ExecCrash
from lib import ExecLock
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import Pixel
from lib import Pos
from lib import Script

ENCOUNTER_DIALOG_POS = Pos(670, 430)
SHORT_DIALOG_POS = Pos(560, 455)
OWN_POKEMON_POS = Pos(5, 425)
ROAMER_MAP_POS = Pos(340, 280)
ROAMER_MAP_COLOR = Pixel(32, 60, 28)

langsPath = pathlib.Path(__file__).parent / "langs"


class BDSPScript(Script):
	@abstractmethod
	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		raise NotImplementedError

	@staticmethod
	@abstractmethod
	def requirements() -> tuple[str, ...]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: Config, **kwargs) -> None:
		super().__init__(ser, cap, config, **kwargs)

		tempLang: Optional[str] = kwargs["tempLang"]

		lang = tempLang if tempLang is not None else config.lang

		logging.debug(f"language used for text recognition: {lang}")

		with open(langsPath / (lang + ".txt")) as f:
			self.names = f.readlines()

	@staticmethod
	def parser(*args, **kwargs) -> argparse.ArgumentParser:
		langs = (lang.name[:-4] for lang in langsPath.iterdir())

		# IDK what I'm doing here but it works ¯\_(ツ)_/¯
		p = super(__class__, __class__).parser(*args, **kwargs)
		p.add_argument("-l", "--lang", action="store", choices=langs, default=None, dest="tempLang", help="override lang for this run only (instead of using the one from config)")
		return p

	def checkShinyDialog(self, e: int, delay: float = 2) -> numpy.ndarray:
		logging.debug("waiting for dialog")
		self.awaitPixel(ENCOUNTER_DIALOG_POS, COLOR_WHITE)
		print(f"dialog start{PAD}\r", end="")

		self.awaitNotPixel(ENCOUNTER_DIALOG_POS, COLOR_WHITE)
		print(f"dialog end{PAD}\r", end="")
		t0 = time.time()

		encounterFrame = self.getframe()
		self.awaitPixel(ENCOUNTER_DIALOG_POS, COLOR_WHITE)

		diff = time.time() - t0
		logging.log(LOG_DELAY, f"dialog delay: {diff:.3f}")
		print(f"dialog delay: {diff:.3f}s{PAD}")

		self.waitAndRender(0.5)

		if delay + 10 > diff > delay:
			raise ExecShiny(e, encounterFrame)
		elif diff >= 89:
			raise ExecLock

		return encounterFrame

	def awaitInGame(self) -> None:
		self.awaitPixel(LOADING_SCREEN_POS, COLOR_BLACK)
		logging.debug("startup screen")

		self.whilePixel(LOADING_SCREEN_POS, COLOR_BLACK, 0.5, lambda: self.press(Button.BUTTON_A))
		logging.debug("after startup")

		self.waitAndRender(1)

		frame = self.getframe()
		if numpy.array_equal(frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x], (41, 41, 41)):
			raise ExecCrash

		self.press(Button.BUTTON_A)
		self.waitAndRender(3)

		# loading screen to game
		self.awaitPixel(LOADING_SCREEN_POS, COLOR_BLACK)
		logging.debug("loading screen")
		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_BLACK)

		logging.debug("in game")
		self.waitAndRender(1)

	def resetRoamer(self, e: int) -> numpy.ndarray:
		logging.debug("reset roamer")
		print("travel to Jubilife City", PAD)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_X)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_PLUS)
		self.waitAndRender(1)
		self.press(Button.L_DOWN_LEFT, 3)
		self.press(Button.L_UP_RIGHT, 0.3, render=True)
		self.press(Button.BUTTON_A)
		self.waitAndRender(1.5)
		self.press(Button.BUTTON_A)

		while not self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE):
			# ???
			for _ in range(3):
				self.press(Button.BUTTON_B)
				self.waitAndRender(0.5)

			self.press(Button.L_DOWN_LEFT, 3)
			self.press(Button.L_UP_RIGHT, 0.3, render=True)
			self.press(Button.BUTTON_A)
			self.waitAndRender(1.5)
			self.press(Button.BUTTON_A)

		self.waitAndRender(2)

		self.press(Button.BUTTON_R)
		self.waitAndRender(0.2)
		logging.debug("run towards start location")
		self.press(Button.L_LEFT, 0.8)
		self.press(Button.L_DOWN, 6.5)

		areaReloads = 0
		while True:
			self.press(Button.BUTTON_R)
			self.waitAndRender(1)
			encounter = self.awaitNearPixel(ROAMER_MAP_POS, ROAMER_MAP_COLOR, 45, 3)

			self.press(Button.BUTTON_R)
			self.waitAndRender(1)

			if encounter is True:
				logging.debug(f"found after reloading area {areaReloads} times")
				logging.debug("roamer in area")
				self.press(Button.L_UP, 0.3)
				self.waitAndRender(0.1)

				logging.debug("open backpack")
				self.press(Button.BUTTON_X)
				self.waitAndRender(0.5)

				self.press(Button.L_UP)
				self.waitAndRender(0.1)
				self.press(Button.L_RIGHT)
				self.waitAndRender(0.1)
				self.press(Button.L_RIGHT)
				self.waitAndRender(0.1)

				self.press(Button.BUTTON_A)
				self.waitAndRender(1.5)

				for _ in range(4):
					self.press(Button.L_RIGHT)
					self.waitAndRender(0.1)

				logging.debug("use repel")
				self.press(Button.BUTTON_A)
				self.waitAndRender(1)
				self.press(Button.BUTTON_A)
				self.waitAndRender(1)
				self.press(Button.BUTTON_A)
				for _ in range(4):
					self.waitAndRender(1)
					self.press(Button.BUTTON_B)

				self._ser.write(b"a")

				_directions = cycle(("a", "d"))
				logging.debug("go for encounter")
				tEnd = time.time() + 2
				frame = self.getframe()
				while not numpy.array_equal(
					frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x],
					COLOR_WHITE.tpl,
				):
					if time.time() > tEnd:
						self._ser.write(next(_directions).encode())
						tEnd = time.time() + 0.5
					if numpy.array_equal(frame[SHORT_DIALOG_POS.y][SHORT_DIALOG_POS.x], COLOR_WHITE):
						self._ser.write(b"0")
						logging.debug("re-apply repel")
						# repel used up
						for d in (2, 1, 1):
							self.waitAndRender(d)
							self.press(Button.BUTTON_A)
						self.waitAndRender(1)
						self.press(Button.BUTTON_A, 0.5)
					frame = self.getframe()

				print("encounter!", PAD)

				self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)
				return self.checkShinyDialog(e, 1.5)
			else:
				logging.debug("reload area")
				areaReloads += 1
				self.press(Button.L_UP, 2)
				self.press(Button.L_DOWN, 2.1)

	def runFromEncounter(self) -> None:
		logging.debug("run from encounter")
		while True:
			self.press(Button.L_UP)
			self.waitAndRender(0.5)
			self.press(Button.BUTTON_A)
			self.waitAndRender(0.5)
			self.press(Button.BUTTON_B)

			if self.awaitPixel(OWN_POKEMON_POS, COLOR_BLACK, 10):
				logging.debug("fade out", PAD)
				break
			else:
				self.waitAndRender(15)
				logging.debug("failed to run or wrong option selected (due to lag, or some other thing)")

		self.awaitNotPixel(OWN_POKEMON_POS, COLOR_BLACK)
		logging.debug("return to game")
		self.waitAndRender(1)

	def getName(self) -> Optional[str]:
		frame = cv2.cvtColor(self.getframe(), cv2.COLOR_BGR2GRAY)
		crop = frame[30:54, 533:641]
		text = pytesseract.image_to_string(crop)

		try:
			return difflib.get_close_matches(str(text).strip(), self.names, n=1)[0]
		except IndexError:
			return None
