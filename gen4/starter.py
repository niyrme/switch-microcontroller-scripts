#!/usr/bin/env python3
import argparse
import sys
import time

import cv2
import serial

import lib
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import Pixel
from lib import Pos
from lib import ReturnCode
from lib.gen4 import ENCOUNTER_DIALOG_POS


SERIAL_DEFAULT = "COM5" if sys.platform == "win32" else "/dev/ttyUSB0"


def p(s: str) -> None:
	print(f"{s}{PAD}\r", end="")


def _main(ser: serial.Serial, vid: cv2.VideoCapture, e: int, **kwargs) -> tuple[int, ReturnCode]:
	starter: int = kwargs.get("starter")
	crashed = False

	# wait for startup screen (black one)
	crashed |= not lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print(f"startup screen", PAD)

	crashed |= not lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print(f"after startup", PAD)

	# in splash screen
	lib.waitAndRender(vid, 1)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 3)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 3)

	# loading screen to game
	crashed |= not lib.awaitPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
	print(f"loading screen", PAD)
	crashed |= not lib.awaitNotPixel(ser, vid, pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)

	if crashed is True:
		return (e, ReturnCode.CRASH)

	print(f"in game", PAD)
	lib.waitAndRender(vid, 1)

	lib.press(ser, vid, "w", duration=0.5)
	lib.waitAndRender(vid, 1)

	# bunch of dialog here
	for _ in range(12):
		lib.waitAndRender(vid, 2)
		lib.press(ser, vid, "A")
	for _ in range(4):
		lib.waitAndRender(vid, 5.5)
		lib.press(ser, vid, "A")
	for _ in range(3):
		lib.waitAndRender(vid, 2)
		lib.press(ser, vid, "A")

	p(f"moving to bag")
	lib.waitAndRender(vid, 7)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 2)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 2)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 5)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 2)
	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 5)

	p(f"selecting starter")
	lib.press(ser, vid, "B")
	lib.waitAndRender(vid, 2)
	for _ in range(starter - 1):
		lib.press(ser, vid, "d", duration=0.2)
		lib.waitAndRender(vid, 1)

	lib.press(ser, vid, "A")
	lib.waitAndRender(vid, 2)
	lib.press(ser, vid, "w")
	lib.waitAndRender(vid, 0.5)
	lib.press(ser, vid, "A")

	lib.awaitPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=Pixel(255, 255, 255))
	lib.awaitNotPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=Pixel(255, 255, 255))

	lib.waitAndRender(vid, 5)

	lib.awaitPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
	p(f"dialog starly (start)")

	lib.awaitNotPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
	p(f"dialog starly (end)")

	lib.awaitPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
	p(f"dialog starter (start)")

	lib.awaitNotPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
	start = time.time()
	p(f"dialog starter (end)")

	lib.awaitPixel(ser, vid, pos=Pos(5, 425), pixel=Pixel(255, 255, 255))
	diff = time.time() - start

	p(f"dialog delay: {diff:.3f}s{PAD}")

	lib.waitAndRender(vid, 0.5)

	return (e + 1, ReturnCode.SHINY if diff > 2 else ReturnCode.OK)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="reset a specific starter until it's shiny")
	parser.add_argument("starter", type=int, choices={1, 2, 3}, help="which starter to reset (1: Turtwig, 2: Chimchar, 3: Piplup)")

	raise SystemExit(
		lib.mainRunner2(
			"./shinyGrind.json",
			"starterReset",
			_main,
			parser,
		),
	)
