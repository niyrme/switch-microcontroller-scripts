import cv2
import numpy
import serial

import lib
from lib import COLOR_BLACK
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import Pos


ENCOUNTER_DIALOG_POS = Pos(670, 430)
OWN_POKEMON_POS = Pos(5, 425)


def awaitInGame(ser: serial.Serial, vid: cv2.VideoCapture) -> None:
	crashed = not lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print("startup screen", PAD)

	crashed |= not lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print("after startup", PAD)

	if crashed is True:
		raise lib.RunCrash

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


def awaitInGameSpam(ser: serial.Serial, vid: cv2.VideoCapture) -> None:
	lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print("startup screen", PAD)

	lib.whilePixel(ser, vid, LOADING_SCREEN_POS, COLOR_BLACK, 0.5, lambda: lib.press(ser, vid, "A"))
	print("after startup", PAD)

	lib.waitAndRender(vid, 1)

	frame = lib.getframe(vid)
	if numpy.array_equal(frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x], (41, 41, 41)):
		raise lib.RunCrash

	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 3)

	# loading screen to game
	crashed = not lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print("loading screen", PAD)
	crashed |= not lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)

	if crashed is True:
		raise lib.RunCrash

	print("in game", PAD)
	lib.waitAndRender(vid, 1)
