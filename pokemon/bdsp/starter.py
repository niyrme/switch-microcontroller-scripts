import argparse
import time

import cv2
import numpy
import serial

import lib
from lib import COLOR_WHITE
from lib import Config
from lib import PAD
from lib import ReturnCode
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import Gen4Script
from lib.pokemon.bdsp import OWN_POKEMON_POS


class Script(Gen4Script):
	scriptName = "starter"

	@staticmethod
	def parser() -> argparse.ArgumentParser:
		p = argparse.ArgumentParser(description="reset starter", add_help=False)
		p.add_argument("starter", type=int, choices={1, 2, 3}, help="which starter to reset (1: Turtwig, 2: Chimchar, 3: Piplup)")
		return p

	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		super().__init__(ser, vid, config, **kwargs, windowName="Pokermans: Starter")

		self.starter = int(kwargs["starter"])
		self.extraStats.append(("Resetting for", ("Turtwig", "Chimchar", "Piplup")[self.starter - 1]))

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGameSpam()

		self.press("w", 0.5)
		self.waitAndRender(1)

		for _ in range(12):
			self.waitAndRender(2)
			self.press("A")
		for _ in range(4):
			self.waitAndRender(5.5)
			self.press("A")
		for _ in range(3):
			self.waitAndRender(2)
			self.press("A")

		print(f"move to bag{PAD}\r", end="")
		for v in (7, 2, 2, 5, 2, 5):
			self.waitAndRender(v)
			self.press("A")

		print(f"select starter{PAD}\r", end="")
		self.press("B")
		self.waitAndRender(2)
		for _ in range(self.starter - 1):
			self.press("d", duration=0.2)
			self.waitAndRender(1)

		self.press("A")
		self.waitAndRender(2)
		self.press("w")
		self.waitAndRender(0.5)
		self.press("A")

		self.awaitFlash(ENCOUNTER_DIALOG_POS, COLOR_WHITE)

		self.waitAndRender(5)

		self.awaitFlash(ENCOUNTER_DIALOG_POS, COLOR_WHITE)
		self.awaitFlash(ENCOUNTER_DIALOG_POS, COLOR_WHITE)

		encounterFrame = self.getframe()

		t0 = time.time()
		crash = self.awaitPixel(OWN_POKEMON_POS, COLOR_WHITE)
		diff = time.time() - t0

		print(f"dialog delay: {diff:.3f}s", PAD)

		if diff >= 89 or crash is True:
			raise lib.RunCrash

		return (e + 1, ReturnCode.SHINY if 15 > diff > 2 else ReturnCode.OK, encounterFrame)
