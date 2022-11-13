import difflib
import sys
import time
from abc import abstractmethod
from itertools import cycle
from typing import Any
from typing import Final
from typing import final
from typing import Optional

import cv2
import pytesseract
import serial

from . import ExecShiny
from . import LOG_DELAY
from . import PokemonScript
from lib import Button
from lib import Capture
from lib import Color
from lib import ExecCrash
from lib import ExecLock
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import Pos
from lib import ScriptT


ENCOUNTER_DIALOG_POS_1: Final[Pos] = Pos(55, 400)
ENCOUNTER_DIALOG_POS_2: Final[Pos] = Pos(670, 430)
OWN_POKEMON_POS: Final[Pos] = Pos(5, 425)
ROAMER_MAP_COLOR: Final[Color] = Color(32, 60, 28)
ROAMER_MAP_POS: Final[Pos] = Pos(340, 280)
SHORT_DIALOG_POS_1: Final[Pos] = Pos(154, 400)
SHORT_DIALOG_POS_2: Final[Pos] = Pos(560, 455)


class BDSPScript(PokemonScript[ScriptT]):
	@abstractmethod
	def main(self, e: int) -> tuple[int, Frame]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: dict[str, Any], **kwargs) -> None:
		super().__init__(ser, cap, config, **kwargs)

		self.configBDSP: Final[dict[str, Any]] = self.configPokemon.pop("bdsp")

		self.sendAllEncounters: Final[bool] = self.configBDSP.pop("sendAllEncounters", False)
		self.showLastRunDuration: Final[bool] = self.configBDSP.pop("showLastRunDuration", False)
		self.showBnp: Final[bool] = self.configBDSP.pop("showBnp", False)

		self._lastDelay: float = 0.0
		self._maxDelay: float = 0.0

	@property
	@abstractmethod
	def target(self) -> str:
		raise NotImplementedError

	def checkShinyDialog(self, e: int, delay: float = 2) -> Frame:
		self._cap.startCapture("encounter")

		print("waiting for dialog")
		self.logDebug("waiting for dialog")
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

		self._lastDelay = diff = round(time.time() - t0, 3)
		self._maxDelay = max(self._maxDelay, diff)

		self.log(LOG_DELAY, f"dialog delay: {diff:>.03f}s")
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
		self.logDebug("startup screen")

		self.whileColor(LOADING_SCREEN_POS, Color.Black(), 0.5, lambda: self.press(Button.BUTTON_A))
		self.logDebug("after startup")

		self.waitAndRender(1)

		if self.getframe().colorAt(LOADING_SCREEN_POS) == Color(41, 41, 41):
			raise ExecCrash

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)

		# loading screen to game
		self.awaitColor(LOADING_SCREEN_POS, Color.Black())
		self.logDebug("loading screen")
		self.awaitNotColor(LOADING_SCREEN_POS, Color.Black())

		self.logDebug("in game")
		self.waitAndRender(1)

	def resetRoamer(self, e: int) -> Frame:
		self.logDebug("reset roamer")
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
		self.logDebug("run towards start location")
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
				self.logDebug(f"roamer found after reloading area {areaReloads} times")
				self.press(Button.L_UP, 0.3)
				self.waitAndRender(0.1)

				self.logDebug("open backpack")
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

				self.logDebug("use repel")
				self.pressN(Button.BUTTON_A, 3, 1, render=True)
				self.pressN(Button.BUTTON_B, 5, 1, render=True)

				self._ser.write(b"a")

				_directions = cycle(("a", "d"))
				self.logDebug("go for encounter")
				tEnd = time.time() + 2

				while (frame := self.getframe()).colorAt(LOADING_SCREEN_POS) != Color.White():
					if time.time() > tEnd:
						self._ser.write(next(_directions).encode())
						tEnd = time.time() + 0.5

					if frame.colorAt(SHORT_DIALOG_POS_2) == Color.White():
						self._ser.write(b"0")
						self.logDebug("re-apply repel")
						# repel used up
						for d in (2, 1, 1):
							self.waitAndRender(d)
							self.press(Button.BUTTON_A)
						self.waitAndRender(1)
						self.press(Button.BUTTON_A, 0.5)

				print("encounter!")

				self.awaitNotColor(LOADING_SCREEN_POS, Color.White())
				return self.checkShinyDialog(e, 1.5)
			else:
				self.logDebug("reload area")
				areaReloads += 1
				self.press(Button.L_UP, 2)
				self.press(Button.L_DOWN, 2.1)

	@final
	def runFromEncounter(self) -> None:
		self.logDebug("run from encounter")
		while True:
			self.press(Button.L_UP)
			self.waitAndRender(0.5)
			self.press(Button.BUTTON_A)
			self.waitAndRender(0.5)
			self.press(Button.BUTTON_B)

			self.logDebug("wait for black out")
			try:
				self.awaitNearColor(OWN_POKEMON_POS, Color.Black(), distance=50, timeout=10)
				self.logDebug("black out")
				break
			except ExecLock:
				self.waitAndRender(15)
				self.logDebug("failed to run or wrong option selected (due to lag, or some other thing)")

		self.awaitNotColor(OWN_POKEMON_POS, Color.Black())
		self.logDebug("return to game")
		self.waitAndRender(1)

	def getName(self) -> Optional[str]:
		self.waitAndRender(20)

		frame = cv2.cvtColor(self.getframe().ndarray, cv2.COLOR_BGR2GRAY)
		cv2.imwrite("logs/shinyFrame.png", frame)
		crop = frame[30:54, 533:641]
		cv2.imwrite("logs/crop.png", crop)
		text = (pytesseract.image_to_string(crop)).strip()

		try:
			return difflib.get_close_matches(text, self._names, n=1)[0]
		except IndexError:
			self.logDebug(f'Failed to parse name from "{text}"')
			return None
