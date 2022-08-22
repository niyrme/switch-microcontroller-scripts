import argparse
import difflib
import time
from typing import Any
from typing import Optional

import cv2
import numpy
import pytesseract

import lib
from lib import Button
from lib import COLOR_WHITE
from lib import PAD
from lib.pokemon import ExecShiny
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import OWN_POKEMON_POS


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of transition into Lake Verity",)

	@staticmethod
	def parser(*args, **kwargs) -> argparse.ArgumentParser:
		p = super(BDSPScript, BDSPScript).parser(*args, **kwargs, description="reset starter")
		p.add_argument("starter", type=int, choices={1, 2, 3}, help="which starter to reset (1: Turtwig, 2: Chimchar, 3: Piplup)")
		return p

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)

		self._starter = int(kwargs.pop("starter"))
		self._starterName = ("Turtwig", "Chimchar", "Piplup")[self._starter - 1]

	@property
	def extraStats(self) -> tuple[tuple[str, Any], ...]:
		return super().extraStats + (
			("resetting for", self._starterName),
		)

	def getName(self) -> Optional[str]:
		frame = cv2.cvtColor(self.getframe(), cv2.COLOR_BGR2GRAY)
		crop = frame[400:420, 15:115]
		text = pytesseract.image_to_string(crop)

		try:
			return difflib.get_close_matches(str(text).strip(), self._names, n=1)[0]
		except IndexError:
			return None

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.L_UP, 0.5)
		self.waitAndRender(1)

		self.pressN(Button.BUTTON_A, 12, 2, render=True)
		self.pressN(Button.BUTTON_A, 4, 5.5, render=True)
		self.pressN(Button.BUTTON_A, 3, 2, render=True)

		print(f"move to bag{PAD}\r", end="")
		for v in (7, 2, 2, 5, 2, 5):
			self.waitAndRender(v)
			self.press(Button.BUTTON_A)

		print(f"select starter{PAD}\r", end="")
		self.press(Button.BUTTON_B)
		self.waitAndRender(2)
		for _ in range(self._starter - 1):
			self.press(Button.L_RIGHT, duration=0.2)
			self.waitAndRender(1)

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)
		self.press(Button.L_UP)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)

		self.awaitFlash(ENCOUNTER_DIALOG_POS, COLOR_WHITE)

		self.waitAndRender(5)

		self.awaitFlash(ENCOUNTER_DIALOG_POS, COLOR_WHITE)
		self.awaitFlash(ENCOUNTER_DIALOG_POS, COLOR_WHITE)

		encounterFrame = self.getframe()

		t0 = time.time()
		crash = self.awaitColor(OWN_POKEMON_POS, COLOR_WHITE)
		diff = time.time() - t0

		print(f"dialog delay: {diff:.3f}s", PAD)

		if 15 > diff > 2:
			raise ExecShiny(e + 1, encounterFrame)
		elif diff >= 89 or crash is True:
			raise lib.ExecLock
		else:
			return (e + 1, encounterFrame)