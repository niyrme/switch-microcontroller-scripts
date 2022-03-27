import argparse
import os
import time
from collections.abc import Generator
from datetime import datetime
from datetime import timedelta

import cv2
import numpy
import serial

import lib
from lib import COLOR_BLACK
from lib import COLOR_WHITE
from lib import PAD
from lib.gen4 import ENCOUNTER_DIALOG_POS
from lib.gen4 import OWN_POKEMON_POS


chanceModifier = int
CHANCE_NORMAL: chanceModifier = 4096
CHANCE_SHINY_CHARM: chanceModifier = 1365


def p(s: str) -> None:
	print(f"{s}{PAD}\r", end="")


def calcChance(n: int, baseChance: chanceModifier = CHANCE_NORMAL) -> float:
	return 1 - ((baseChance - 1) / baseChance) ** n


def _main(encountersStart: int, ser: serial.Serial) -> Generator[int, None, None]:
	now = datetime.now()
	screenshotDir = os.path.join(
		"screenshots",
		f"{now.strftime('%Y-%m-%d')}",
		f"{now.strftime('%H-%M-%S')}",
	)
	os.makedirs(screenshotDir, exist_ok=True)

	parser = argparse.ArgumentParser(prog="Shiny Grind", description="runs around and makes a sound when encountering a shiny Pokémon")
	parser.add_argument("direction", type=str, choices={"h", "v"}, help="direction to run in {(h)orizontal, (v)ertical} direction")
	parser.add_argument("delay", type=float, help="delay betweeen changing direction")
	parser.add_argument("--shiny-charm", action="store_true", dest="hasShinyCharm")
	args = parser.parse_args()

	directions: dict[str, tuple[str, str]] = { "h": ("a", "d"), "v": ("w", "s")}
	direction1, direction2 = directions[args.direction]

	toggleDelay: float = args.delay
	tStart = datetime.now()

	chanceMod = (CHANCE_NORMAL, CHANCE_SHINY_CHARM)[int(args.hasShinyCharm)]

	print("setting up cv2. this may take a while...")
	vid = cv2.VideoCapture(0)
	vid.set(cv2.CAP_PROP_FRAME_WIDTH, 768)
	vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

	lib.press(ser, vid, "B")
	ser.write("B".encode())
	time.sleep(0.1)
	ser.write(b"0")
	time.sleep(0.1)

	encountersCurrent = 0

	while True:
		encounter = encountersStart + encountersCurrent
		runDelta = datetime.now() - tStart
		runDelta = timedelta(days=runDelta.days, seconds=runDelta.seconds)
		print("\033c", end="")
		print(f"encounters since last shiny: ({encountersCurrent}/{encounter}) ({(calcChance(encounter, chanceMod) * 100):.2f}%) (running for: {runDelta})")

		ser.write(b"0")
		toggle = encounter % 2 == 0
		tEnd = time.time()
		frame = lib.getframe(vid)
		while not numpy.array_equal(
			frame[ENCOUNTER_DIALOG_POS.y][ENCOUNTER_DIALOG_POS.x],
			COLOR_WHITE.tpl(),
		):
			if time.time() > tEnd:
				ser.write(( direction1, direction2)[int(toggle)].encode())
				toggle = not toggle
				tEnd = time.time() + toggleDelay
			frame = lib.getframe(vid)
		ser.write(b"0")

		# wait for fade-out to be gone
		lib.awaitNotPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)

		# wait for dialog box "Wild {Pokemon} appeared"
		lib.awaitPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
		p("dialog started")

		# save screenshot of encounter
		cv2.imwrite(f"{screenshotDir}/{encounter}.jpg", lib.getframe(vid))

		lib.awaitNotPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
		p("dialog ended")

		t0 = time.time()

		lib.awaitPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)

		t1 = time.time()
		diff = t1 - t0
		print(f"dialog delay: {diff:.3f}s{PAD}")

		encountersCurrent += 1
		yield encountersStart + encountersCurrent

		if 16 > diff > 1.5:
			ser.write(b"0")
			print("SHINY!!")
			print("SHINY!!")
			print("SHINY!!")
			print("\a")
			encountersStart = encountersCurrent = 0
			yield 0

			lib.alarm(ser, vid)
			try:
				while True:
					if time.time() % 5 == 0:
						print("\a")
					lib.getframe(vid)
			except KeyboardInterrupt:
				pass

			cmd = input("continue? (y/n)").strip().lower()
			if cmd in ("y", "yes"):
				continue
			else:
				raise lib.RunStop

		# wait until own dialog box appears
		lib.awaitPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
		p("own dialog start")
		# wait until own dialog box is gone
		lib.awaitNotPixel(ser, vid, pos=ENCOUNTER_DIALOG_POS, pixel=COLOR_WHITE)
		p("own dialog end")

		# wait until UI is done loading
		lib.awaitPixel(ser, vid, pos=OWN_POKEMON_POS, pixel=COLOR_WHITE)
		lib.waitAndRender(vid, 1)
		p("ready")

		while True:
			lib.press(ser, vid, "w")
			lib.waitAndRender(vid, 0.5)
			lib.press(ser, vid, "A")
			lib.waitAndRender(vid, 1)
			lib.press(ser, vid, "B")

			if lib.awaitPixel(ser, vid, pos=OWN_POKEMON_POS, pixel=COLOR_BLACK, timeout=8):
				p("fade out")
				break
			else:
				lib.waitAndRender(vid, 10)

		lib.awaitNotPixel(ser, vid, pos=OWN_POKEMON_POS, pixel=COLOR_BLACK)
		print("return to game")
		lib.waitAndRender(vid, 0.5)


if __name__ == "__main__":
	raise SystemExit(
		lib.mainRunner(
			"./shinyGrind.json",
			"randomEncounters",
			_main,
		),
	)
