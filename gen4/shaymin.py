import sys
from argparse import ArgumentParser

import cv2
import numpy
import serial

import lib
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import ReturnCode
from lib.gen4 import ENCOUNTER_DIALOG_POS


SERIAL_DEFAULT = "COM5" if sys.platform == "win32" else "/dev/ttyUSB0"


def _main(ser: serial.Serial, vid: cv2.VideoCapture, e: int, **kwargs) -> tuple[int, ReturnCode, numpy.ndarray]:
	lib.resetGame(ser, vid)
	crashed = False

	# wait for startup screen (black one)
	crashed |= not lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print("startup screen", PAD)

	crashed |= not lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print("after startup", PAD)

	# in splash screen
	lib.waitAndRender(vid, 1)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 3)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 3)

	# loading screen to game
	crashed |= not lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print("loading screen", PAD)
	crashed |= not lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)

	if crashed is True:
		raise lib.RunCrash

	print("in game", PAD)
	lib.waitAndRender(vid, 1)

	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 3)
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
			"shaymin",
			_main,
			ArgumentParser(description="reset Shaymin automatically"),
		),
	)
