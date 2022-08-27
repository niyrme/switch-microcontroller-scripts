import difflib
import logging
import sys
import time
from abc import abstractmethod
from itertools import cycle
from typing import Any
from typing import Optional

import cv2
import pytesseract
import serial

from . import ExecShiny
from . import LOG_DELAY
from lib import Button
from lib import Capture
from lib import Color
from lib import Config
from lib import ExecCrash
from lib import ExecLock
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import Pos
from lib.pokemon import PokemonScript

ENCOUNTER_DIALOG_POS_1 = Pos(55, 400)
ENCOUNTER_DIALOG_POS_2 = Pos(670, 430)
SHORT_DIALOG_POS = Pos(560, 455)
OWN_POKEMON_POS = Pos(5, 425)
ROAMER_MAP_POS = Pos(340, 280)
ROAMER_MAP_COLOR = Color(32, 60, 28)


class BDSPScript(PokemonScript):
	@abstractmethod
	def main(self, e: int) -> tuple[int, Frame]:
		raise NotImplementedError

	@staticmethod
	@abstractmethod
	def requirements() -> tuple[str, ...]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: Config, **kwargs) -> None:
		super().__init__(ser, cap, config, **kwargs)

		self.configBDSP: dict[str, Any] = self.configPokemon.pop("bdsp")

		self.sendAllEncounters: bool = self.configBDSP.pop("sendAllEncounters", False)
		self.showLastRunDuration: bool = self.configBDSP.pop("showLastRunDuration", False)
		self.showBnp: bool = self.configBDSP.pop("showBnp", False)

		self._showMaxDelay: bool = self.configBDSP.pop("showMaxDelay", False)
		self._maxDelay: float = 0

		self._showLastDelay: bool = self.configBDSP.pop("showLastDelay", False)
		self._lastDelay: float = 0

	@property
	def extraStats(self) -> tuple[tuple[str, Any], ...]:
		s = []
		if self._showLastDelay is True: s.append(("Last delay", self._lastDelay))
		if self._showMaxDelay is True: s.append(("Max delay", self._maxDelay))
		return super().extraStats + tuple(s)

	@property
	def target(self) -> str:
		return "Unknown"

	def checkShinyDialog(self, e: int, delay: float = 2) -> Frame:
		logging.debug("waiting for dialog")
		self.awaitColors((
			(ENCOUNTER_DIALOG_POS_1, Color.White()),
			(ENCOUNTER_DIALOG_POS_2, Color.White()),
		))
		print(f"dialog start{' ' * 30}\r", end="")

		self.awaitNotColors((
			(ENCOUNTER_DIALOG_POS_1, Color.White()),
			(ENCOUNTER_DIALOG_POS_2, Color.White()),
		))
		print(f"dialog end{' ' * 30}\r", end="")
		t0 = time.time()

		encounterFrame = self.getframe()
		self.awaitColors((
			(ENCOUNTER_DIALOG_POS_1, Color.White()),
			(ENCOUNTER_DIALOG_POS_2, Color.White()),
		))

		diff = round(time.time() - t0, 3)
		self._lastDelay = diff
		self._maxDelay = max(self._maxDelay, diff)

		logging.log(LOG_DELAY, f"dialog delay: {diff:.3f}s")
		print(f"dialog delay: {diff}s")

		self.waitAndRender(0.5)

		if delay + 10 > diff > delay:
			raise ExecShiny(e + 1, encounterFrame)
		elif diff >= 89:
			raise ExecLock("checking shiny dialog timed out")
		else:
			return encounterFrame

	def awaitInGame(self) -> None:
		self.awaitColor(LOADING_SCREEN_POS, Color.Black())
		logging.debug("startup screen")

		self.whileColor(LOADING_SCREEN_POS, Color.Black(), 0.5, lambda: self.press(Button.BUTTON_A))
		logging.debug("after startup")

		self.waitAndRender(1)

		frame = self.getframe()
		if frame.colorAt(LOADING_SCREEN_POS) == Color(41, 41, 41):
			raise ExecCrash

		self.press(Button.BUTTON_A)
		self.waitAndRender(3)

		# loading screen to game
		self.awaitColor(LOADING_SCREEN_POS, Color.Black())
		logging.debug("loading screen")
		self.awaitNotColor(LOADING_SCREEN_POS, Color.Black())

		logging.debug("in game")
		self.waitAndRender(1)

	def resetRoamer(self, e: int) -> Frame:
		logging.debug("reset roamer")
		print("travel to Jubilife City")
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

		while True:
			try:
				self.awaitFlash(LOADING_SCREEN_POS, Color.White())
			except ExecLock as ex:
				print(ex, file=sys.stderr)
				self.pressN(Button.BUTTON_B, 3, 0.5, render=True)
				self.press(Button.L_DOWN_LEFT, 3)
				self.press(Button.L_UP_RIGHT, 0.3, render=True)
				self.press(Button.BUTTON_A)
				self.waitAndRender(1.5)
				self.press(Button.BUTTON_A)
			else:
				break

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
			encounter = self.awaitNearColor(ROAMER_MAP_POS, ROAMER_MAP_COLOR, 45, 3)

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

				self.pressN(Button.L_RIGHT, 4, 0.1, render=True)

				logging.debug("use repel")
				self.pressN(Button.BUTTON_A, 3, 1, render=True)
				self.pressN(Button.BUTTON_B, 5, 1, render=True)

				self._ser.write(b"a")

				_directions = cycle(("a", "d"))
				logging.debug("go for encounter")
				tEnd = time.time() + 2
				frame = self.getframe()
				while frame.colorAt(LOADING_SCREEN_POS) != Color.White():
					if time.time() > tEnd:
						self._ser.write(next(_directions).encode())
						tEnd = time.time() + 0.5

					if frame.colorAt(SHORT_DIALOG_POS) == Color.White():
						self._ser.write(b"0")
						logging.debug("re-apply repel")
						# repel used up
						for d in (2, 1, 1):
							self.waitAndRender(d)
							self.press(Button.BUTTON_A)
						self.waitAndRender(1)
						self.press(Button.BUTTON_A, 0.5)
					frame = self.getframe()

				print("encounter!")

				self.awaitNotColor(LOADING_SCREEN_POS, Color.White())
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

			if self.awaitColor(OWN_POKEMON_POS, Color.Black(), 10):
				logging.debug("fade out")
				break
			else:
				self.waitAndRender(15)
				logging.debug("failed to run or wrong option selected (due to lag, or some other thing)")

		self.awaitNotColor(OWN_POKEMON_POS, Color.Black())
		logging.debug("return to game")
		self.waitAndRender(1)

	def getName(self) -> Optional[str]:
		frame = cv2.cvtColor(self.getframe().ndarray, cv2.COLOR_BGR2GRAY)
		crop = frame[30:54, 533:641]
		text = pytesseract.image_to_string(crop)

		try:
			return difflib.get_close_matches(str(text).strip(), self._names, n=1)[0]
		except IndexError:
			return None
