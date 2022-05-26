import cv2
import numpy
import serial

from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import Config
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import ReturnCode
from lib import RunCrash
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS
from lib.pokemon.bdsp import Gen4Script
from lib.pokemon.bdsp import SHORT_DIALOG_POS


class Script(Gen4Script):
	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		super().__init__(ser, vid, config, **kwargs, windowName="Pokermans: Heatran")

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
		crashed |= not self.awaitNotPixel(pos=SHORT_DIALOG_POS, pixel=COLOR_BLACK)

		if crashed is True:
			raise RunCrash

		print("in game", PAD)
		self.waitAndRender(1)

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		self.awaitInGameSpam()

		self.waitAndRender(2)

		self.press("A")
		self.awaitPixel(SHORT_DIALOG_POS, COLOR_WHITE)
		self.waitAndRender(0.5)
		self.press("A")
		self.waitAndRender(0.5)
		self.press("A")

		self.waitAndRender(3)
		self.awaitFlash(LOADING_SCREEN_POS, COLOR_WHITE)

		print("waiting for dialog", PAD)

		rc, encounterFrame = self.checkShinyDialog(ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
		return (e + 1, rc, encounterFrame)
