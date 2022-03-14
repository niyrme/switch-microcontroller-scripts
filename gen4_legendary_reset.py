import time
from argparse import ArgumentParser

import cv2
import serial

import lib
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import ReturnCode
from lib.gen4 import ENCOUNTER_DIALOG_POS


def _main(ser: serial.Serial, vid: cv2.VideoCapture, e: int, **kwargs) -> tuple[int, ReturnCode]:
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
	lib.awaitPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
	print(f"legendary dialog start{PAD}\r", end="")
	lib.awaitNotPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
	print(f"legendary dialog end{PAD}\r", end="")
	t0 = time.time()

	lib.awaitPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
	t1 = time.time()

	diff = t1 - t0
	print(f"dialog delay: {diff:.3f}s{PAD}")

	lib.waitAndRender(vid, 0.5)

	return (e + 1, ReturnCode.SHINY if diff > 1.5 else ReturnCode.OK)


if __name__ == "__main__":
	raise SystemExit(
     lib.mainRunner2(
      "./shinyGrind.json",
      "pixieEncounter",
      _main,
      ArgumentParser(description="reset Dialga or Palkia automatically"),
     ),
 )
