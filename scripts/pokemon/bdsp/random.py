import argparse
import logging
import time
from itertools import cycle
from typing import Literal

import numpy

from lib import Button
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import PAD
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

		direction: Literal["h", "v"] = kwargs["direction"]
		assert direction in ("h", "v")

		self.directions = cycle(
			(Button.L_LEFT, Button.L_RIGHT)
			if direction == "h"
			else (Button.L_UP, Button.L_DOWN),
		)

		self.delay = float(kwargs["delay"])

		logging.debug(f"directions: {self.directions}")
		logging.debug(f"delay: {self.delay}")

	def main(self, e: int) -> tuple[int, numpy.ndarray]:
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

		encounterFrame = self.checkShinyDialog(0, 1.5)

		self.whileNotPixel(OWN_POKEMON_POS, COLOR_WHITE, 0.5, lambda: self.press(Button.BUTTON_B))
		self.waitAndRender(1)

		self.runFromEncounter()

		return (e + 1, encounterFrame)
