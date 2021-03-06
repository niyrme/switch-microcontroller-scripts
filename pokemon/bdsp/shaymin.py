import cv2
import numpy
import serial

from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import Config
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import ReturnCode
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import Gen4Script
from lib.pokemon.bdsp import OWN_POKEMON_POS


class Script(Gen4Script):
	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		super().__init__(ser, vid, config, **kwargs, windowName="Pokermans: Shaymin")

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.press("A")
		self.waitAndRender(3)
		self.press("A")
		self.waitAndRender(2.5)

		self.awaitPixel(LOADING_SCREEN_POS, COLOR_WHITE)
		self.awaitNotPixel(LOADING_SCREEN_POS, COLOR_WHITE)

		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
		if rc == ReturnCode.SHINY:
			return (e + 1, ReturnCode.SHINY, encounterFrame)

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
		print("return to game")
		self.waitAndRender(1)

		self.press("A")
		self.waitAndRender(0.5)

		self.press("s", 3.5)
		self.press("w", 3.8)
		return (e + 1, ReturnCode.OK, encounterFrame)
