import argparse
import logging
import time
from itertools import cycle
from typing import Literal

import numpy

from lib import Button
from lib import Color
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import OWN_POKEMON_POS


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return (
			"Stand in a patch of grass with enough tiles (could take some time otherwise)",
			"No repel active",
		)

	@staticmethod
	def parser(*args, **kwargs) -> argparse.ArgumentParser:
		p = super(__class__, __class__).parser(*args, **kwargs, description="reset random encounters")
		p.add_argument("direction", type=str, choices={"h", "v"}, help="direction to run in {(h)orizontal, (v)ertical} direction")
		p.add_argument("delay", type=float, help="delay betweeen changing direction")
		return p

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)

		direction: Literal["h", "v"] = kwargs.pop("direction")
		assert direction in ("h", "v")

		self._directions = cycle(
			(Button.L_LEFT, Button.L_RIGHT)
			if direction == "h"
			else (Button.L_UP, Button.L_DOWN),
		)

		self._delay = float(kwargs.pop("delay"))

		logging.debug(f"directions: {self._directions}")
		logging.debug(f"delay: {self._delay}")

	@property
	def target(self) -> str:
		return "Random"

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
		tEnd = time.time()
		frame = self.getframe()

		while not numpy.array_equal(
			frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x],
			Color.White().tpl,
		):
			if time.time() > tEnd:
				self._ser.write(next(self._directions).encode())
				tEnd = time.time() + self._delay
			frame = self.getframe()
		print("encounter!")
		self._ser.write(b"0")

		self.awaitNotColor(LOADING_SCREEN_POS, Color.White())

		encounterFrame = self.checkShinyDialog(0, 1.5)

		self.whileNotColor(OWN_POKEMON_POS, Color.White(), 0.5, lambda: self.press(Button.BUTTON_B))
		self.waitAndRender(1)

		self.runFromEncounter()

		return (e + 1, encounterFrame)
