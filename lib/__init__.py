import argparse
import contextlib
import json
import sys
import time
from collections.abc import Callable
from collections.abc import Generator
from datetime import datetime
from datetime import timedelta
from enum import IntEnum
from typing import Any
from typing import NamedTuple
from typing import TypeVar

import cv2
import numpy
import serial


class StopRun(Exception): ...


class Pos(NamedTuple):
	x: int
	y: int


class Pixel(NamedTuple):
	r: int
	g: int
	b: int

	def tpl(self) -> tuple[int, int, int]:
		return (self.r, self.g, self.b)


class ReturnCode(IntEnum):
	CRASH = -1
	OK = 0
	SHINY = 1


PAD = " " * 32

COLOR_BLACK = Pixel(0, 0, 0)
COLOR_WHITE = Pixel(255, 255, 255)

LOADING_SCREEN_POS = Pos(705, 15)


def alarm(ser: serial.Serial, vid: cv2.VideoCapture) -> None:
	for _ in range(3):
		ser.write(b"!")
		waitAndRender(vid, 1)
		ser.write(b".")
		waitAndRender(vid, 0.4)


def press(ser: serial.Serial, vid: cv2.VideoCapture, s: str, duration: float = .05) -> None:
	print(f"{datetime.now().strftime('%H:%M:%S')} '{s}' for {duration} {PAD}\r", end="")

	ser.write(s.encode())
	if duration >= 0.1:
		tEnd = time.time() + duration
		while tEnd > time.time():
			getframe(vid)
	else:
		time.sleep(duration)
	ser.write(b"0")
	time.sleep(.075)


def getframe(vid: cv2.VideoCapture, windowName = "Pokermans") -> numpy.ndarray:
	_, frame = vid.read()
	cv2.imshow(windowName, frame)
	if cv2.waitKey(1) & 0xFF == ord("q"):
		raise SystemExit(0)
	else:
		return frame


def waitAndRender(vid: cv2.VideoCapture, t: float) -> None:
	end = time.time() + t
	while time.time() < end:
		getframe(vid)


def awaitPixel(
	ser: serial.Serial,
	vid: cv2.VideoCapture,
	*,
	pos: Pos,
	pixel: Pixel,
	timeout: float = 90,
) -> bool:
	end = time.time() + timeout
	frame = getframe(vid)
	while not numpy.array_equal(frame[pos.y][pos.x], pixel.tpl()):
		frame = getframe(vid)
		if time.time() > end:
			return False
	return True


def awaitNotPixel(
	ser: serial.Serial,
	vid: cv2.VideoCapture,
	*,
	pos: Pos,
	pixel: Pixel,
	timeout: float = 90,
) -> bool:
	end = time.time() + timeout
	frame = getframe(vid)
	while numpy.array_equal(frame[pos.y][pos.x], pixel.tpl()):
		frame = getframe(vid)
		if time.time() > end:
			return False
	return True


@contextlib.contextmanager
def shh(ser: serial.Serial) -> Generator[None, None, None]:
	try: yield
	finally: ser.write(b'.')


def resetGame(ser: serial.Serial, vid: cv2.VideoCapture) -> None:
	press(ser, vid, "H")
	waitAndRender(vid, 1)
	press(ser, vid, "X")
	waitAndRender(vid, 1)
	press(ser, vid, "A")
	waitAndRender(vid, 3)
	press(ser, vid, "A")
	waitAndRender(vid, 1)
	press(ser, vid, "A")


def loadJson(filePath: str) -> dict:
	with open(filePath, "r+") as f:
		data: dict = json.load(f)
	return data


def dumpJson(filePath: str, data: dict) -> None:
	with open(filePath, "w") as f:
		json.dump(data, f, indent="\t")


T = TypeVar("T")
K = TypeVar("K")


def jsonGetDefault(data: dict[K, T], key: K, default: T) -> tuple[dict[K, T], T]:
	try:
		return (data, data[key])
	except KeyError:
		return (data | { key: default}, default)


def mainRunner(jsonPath: str, encountersKey: str, mainFn: Callable[[int, serial.Serial], Generator[int, None, None]]) -> int:
	jsn, encounters = jsonGetDefault(
		loadJson(jsonPath),
		encountersKey,
		0,
	)

	_, serialPort = jsonGetDefault(
		loadJson("./config.json"),
		"serialPort",
		"COM0",
	)

	print(f"start encounters: {encounters}")

	try:
		with serial.Serial(serialPort, 9600) as ser, shh(ser):
			for e in mainFn(encounters, ser):
				encounters = e
	except (KeyboardInterrupt, StopRun):
		print("\033c", end="")
	except serial.SerialException as e:
		print(f"failed to open serial connection: {e}", file=sys.stderr)
	finally:
		cv2.destroyAllWindows()
		dumpJson(jsonPath, jsn | { encountersKey: encounters})
		print(f"saved encounters.. ({encounters}){PAD}\n")

	return 0


T_FN = Callable[[serial.Serial, cv2.VideoCapture, int, dict[str, Any]], tuple[int, ReturnCode]]

def _mainRunner(serialPort: str, encountersStart: int, fn: T_FN):
	with serial.Serial(serialPort, 9600) as ser, shh(ser):
		print("setting up cv2. This may take a while...")
		vid: cv2.VideoCapture = cv2.VideoCapture(0)
		vid.set(cv2.CAP_PROP_FPS, 30)
		vid.set(cv2.CAP_PROP_FRAME_WIDTH, 768)
		vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

		ser.write("B".encode())
		time.sleep(0.1)
		ser.write(b"0")
		time.sleep(0.1)

		tStart = datetime.now()
		currentEncounters = 0
		encounters = encountersStart
		crashes = 0

		try:
			while True:
				print("\033c", end="")

				runDelta = datetime.now() - tStart
				avg = runDelta / (currentEncounters if currentEncounters != 0 else 1)

				# remove microseconds from the timedeltas
				runDelta = timedelta(days=runDelta.days, seconds=runDelta.seconds)
				avg = timedelta(days=avg.days, seconds=avg.seconds)

				print(f"running for:  {runDelta} (average per reset: {avg})")
				print(f"encounters:   ({currentEncounters:>03}/{(encounters):>05})")
				print(f"crashes:      {crashes}\n")

				resetGame(ser, vid)
				encounters, code = fn(ser, vid, encounters)

				if code == ReturnCode.CRASH:
					press(ser, vid, "A")
					waitAndRender(vid, 1)
					press(ser, vid, "A")
					crashes += 1
					continue
				elif code == ReturnCode.SHINY:
					ser.write(b"0")
					print("SHINY!!")
					print("SHINY!!")
					print("SHINY!!")
					print("\a")

					try:
						while True:
							if time.time() % 5 == 0:
								print("\a")
							getframe(vid)
					except KeyboardInterrupt:
						pass

					while True:
						cmd = input("continue? (y/n)")
						if cmd in ("y", "yes"):
							break
						elif cmd in ("n", "no"):
							raise StopRun
						else:
							print(f"invalid command: {cmd}")
				elif code == ReturnCode.OK:
					currentEncounters += 1
				else:
					print(f"got invalid return code: {code}")
		except (KeyboardInterrupt, EOFError):
			raise StopRun
		finally:
			vid.release()
			cv2.destroyAllWindows()
			return encounters


def mainRunner2(jsonPath: str, encountersKey: str, mainFn: T_FN, parser: argparse.ArgumentParser = None) -> int:
	jsn, encounters = jsonGetDefault(
		loadJson(jsonPath),
		encountersKey,
		0,
	)

	_, serialPort = jsonGetDefault(
		loadJson("./config.json"),
		"serialPort",
		"COM0",
	)

	print(f"start encounters: {encounters}")

	args = dict()

	if parser is not None:
		args = parser.parse_args()

	try:
		encounters = _mainRunner(serialPort, encounters, mainFn, args)
	except StopRun:
		print("\033c", end="")
	except serial.SerialException as e:
		print(f"failed to open serial connection: {e}", file=sys.stderr)
		return 1
	finally:
		dumpJson(jsonPath, jsn | { encountersKey: encounters})
		print(f"saved encounters.. ({encounters}){PAD}\n")

	return 0
