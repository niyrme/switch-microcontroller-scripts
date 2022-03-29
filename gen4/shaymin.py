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
from lib.gen4 import OWN_POKEMON_POS


def _main(ser: serial.Serial, vid: cv2.VideoCapture, e: int, **kwargs) -> tuple[int, ReturnCode, numpy.ndarray]:
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 3)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 2.5)

	lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_WHITE)
	lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_WHITE)

	# encounter dialog
	rc, encounterFrame = lib.checkShinyDialog(ser, vid, ENCOUNTER_DIALOG_POS, COLOR_WHITE, 1.5)
	if rc == ReturnCode.SHINY:
		return (e + 1, ReturnCode.SHINY, encounterFrame)

	# wait until UI is done loading
	lib.awaitPixel(ser, vid, pos=OWN_POKEMON_POS, pixel=COLOR_WHITE)
	lib.waitAndRender(vid, 1)

	while True:
		lib.press(ser, vid, "w")
		lib.waitAndRender(vid, 0.5)
		lib.press(ser, vid, "A")
		lib.waitAndRender(vid, 1)
		lib.press(ser, vid, "B")

		if lib.awaitPixel(ser, vid, pos=OWN_POKEMON_POS, pixel=COLOR_BLACK, timeout=10):
			print("fade out", PAD)
			break
		else:
			lib.waitAndRender(vid, 10)

	lib.awaitNotPixel(ser, vid, pos=OWN_POKEMON_POS, pixel=COLOR_BLACK)
	print("return to game")
	lib.waitAndRender(vid, 1)

	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 0.5)

	lib.press(ser, vid, "s", 3.5)
	lib.waitAndRender(vid, 0.2)
	lib.press(ser, vid, "w", 3.8)
	return (e + 1, ReturnCode.OK, encounterFrame)


if __name__ == "__main__":
	raise SystemExit(
		lib.mainRunner2(
			"./shinyGrind.json",
			"shaymin",
			_main,
			ArgumentParser(description="reset Shaymin automatically"),
		),
	)
