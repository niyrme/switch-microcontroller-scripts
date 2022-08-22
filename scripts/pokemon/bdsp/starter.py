import argparse
import time
from typing import Any
from typing import Optional

import numpy

import lib
from lib import Button
from lib import Color
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
			("Resetting for", self._starterName),
		)

	@property
	def target(self) -> str:
		return self._starterName

	def getName(self) -> Optional[str]:
		self._starterName

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.L_UP, 0.5)
		self.waitAndRender(1)

		self.pressN(Button.BUTTON_A, 12, 2, render=True)
		self.pressN(Button.BUTTON_A, 4, 5.5, render=True)
		self.pressN(Button.BUTTON_A, 3, 2, render=True)

		print("move to bag")
		for v in (7, 2, 2, 5, 2, 5):
			self.waitAndRender(v)
			self.press(Button.BUTTON_A)

		print("select starter")
		self.press(Button.BUTTON_B)
		self.waitAndRender(2)
		self.pressN(Button.L_RIGHT, self._starter - 1, 1, 0.2, render=True)

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)
		self.press(Button.L_UP)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)

		self.awaitFlash(ENCOUNTER_DIALOG_POS, Color.White())

		self.waitAndRender(5)

		self.awaitFlash(ENCOUNTER_DIALOG_POS, Color.White())
		self.awaitFlash(ENCOUNTER_DIALOG_POS, Color.White())

		encounterFrame = self.getframe()

		t0 = time.time()
		crash = self.awaitColor(OWN_POKEMON_POS, Color.White())
		diff = time.time() - t0

		print(f"dialog delay: {diff:.3f}s")

		if 15 > diff > 2:
			raise ExecShiny(e + 1, encounterFrame)
		elif diff >= 89 or crash is True:
			raise lib.ExecLock
		else:
			return (e + 1, encounterFrame)
