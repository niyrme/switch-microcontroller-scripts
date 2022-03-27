from argparse import ArgumentParser

import cv2
import numpy
import serial

import lib
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import ReturnCode
from lib.gen4 import awaitInGame
from lib.gen4 import ENCOUNTER_DIALOG_POS


def _main(ser: serial.Serial, vid: cv2.VideoCapture, e: int, **kwargs) -> tuple[int, ReturnCode, numpy.ndarray]:
	lib.resetGame(ser, vid)
	awaitInGame(ser, vid)

	# walk towards legendary
	lib.press(ser, vid, "w", duration=0.5)
	lib.waitAndRender(vid, 2)
	lib.press(ser, vid, "B")
	lib.waitAndRender(vid, 0.5)
	lib.press(ser, vid, "B")
	lib.waitAndRender(vid, 0.5)
	lib.press(ser, vid, "B")

	# flash to enter battle
	lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_WHITE)
	lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_WHITE)

	# flash inside battle
	lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_WHITE)
	lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_WHITE)

	# encounter dialog
	rc, encounterFrame = lib.checkShinyDialog(ser, vid, ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
	return (e + 1, rc, encounterFrame)


if __name__ == "__main__":
	raise SystemExit(
		lib.mainRunner2(
			"./shinyGrind.json",
			"legendary",
			_main,
			ArgumentParser(description="reset Dialga or Palkia automatically"),
		),
	)
