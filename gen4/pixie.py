import sys
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


SERIAL_DEFAULT = "COM5" if sys.platform == "win32" else "/dev/ttyUSB0"


def _main(ser: serial.Serial, vid: cv2.VideoCapture, e: int, **kwargs) -> tuple[int, ReturnCode, numpy.ndarray]:
	lib.resetGame(ser, vid)
	awaitInGame(ser, vid)

	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 2)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 2.5)

	lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_WHITE)
	lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_WHITE)

	# encounter dialog
	rc, encounterFrame = lib.checkShinyDialog(ser, vid, ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
	return (e + 1, rc, encounterFrame)


if __name__ == "__main__":
	raise SystemExit(
		lib.mainRunner2(
			"./shinyGrind.json",
			"pixie",
			_main,
			ArgumentParser(description="reset Uxie or Azelf automatically"),
		),
	)
