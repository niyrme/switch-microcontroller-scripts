import argparse
import contextlib
import json
import os
import sys
import time
import uuid
from collections.abc import Callable
from collections.abc import Generator
from datetime import datetime
from datetime import timedelta
from enum import IntEnum
from typing import Any
from typing import NamedTuple
from typing import Optional
from typing import TypeVar

import cv2
import numpy
import serial
import telegram
import telegram_send


class RunStop(Exception): ...
class RunCrash(Exception): ...


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

CFG_NOTIFY: bool = False
CFG_RENDER: bool = True
CFG_SEND_ALL_ENCOUNTERS: bool = False

MAINRUNNER_FUNCTION = Callable[[serial.Serial, cv2.VideoCapture, int], tuple[int, ReturnCode, numpy.ndarray]]


def sendTelegram(**kwargs) -> None:
	if CFG_NOTIFY is True:
		try:
			telegram_send.send(**kwargs)
		except telegram.error.NetworkError as e:
			print(f"telegram_send: connection failed: {e}", file=sys.stderr)


def sendMsg(msg: str) -> None:
	sendTelegram(messages=(msg,))


def sendImg(imgPath: str) -> None:
	with open(imgPath, "rb") as img:
		sendTelegram(images=(img,))


def alarm(ser: serial.Serial, vid: cv2.VideoCapture) -> None:
	for _ in range(3):
		ser.write(b"!")
		waitAndRender(vid, 1)
		ser.write(b".")
		waitAndRender(vid, 0.4)


def press(ser: serial.Serial, vid: cv2.VideoCapture, s: str, duration: float = .05) -> None:
	print(f"{datetime.now().strftime('%H:%M:%S')} '{s}' for {duration} {PAD}\r", end="")

	ser.write(s.encode())
	time.sleep(duration)
	ser.write(b"0")
	time.sleep(.075)


def getframe(vid: cv2.VideoCapture) -> numpy.ndarray:
	_, frame = vid.read()

	if CFG_RENDER is True:
		cv2.imshow("Pokermans", frame)

	if cv2.waitKey(1) & 0xFF == ord("q"):
		raise RunStop
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


def whilePixel(
	ser: serial.Serial,
	vid: cv2.VideoCapture,
	pos: Pos,
	pixel: Pixel,
	delay: float,
	fn: Callable[..., Any],
	fnArgs: dict[str, Any],
) -> None:
	fnArgs |= {"ser": ser, "vid": vid}
	frame = getframe(vid)
	tEnd = time.time() + delay
	while numpy.array_equal(frame[pos.y][pos.x], pixel.tpl()):
		if time.time() > tEnd:
			fn(**fnArgs)
			tEnd = time.time() + delay
		frame = getframe(vid)


def whileNotPixel(
	ser: serial.Serial,
	vid: cv2.VideoCapture,
	pos: Pos,
	pixel: Pixel,
	delay: float,
	fn: Callable[..., Any],
	fnArgs: dict[str, Any],
) -> None:
	fnArgs |= {"ser": ser, "vid": vid}
	frame = getframe(vid)
	tEnd = time.time() + delay
	while not numpy.array_equal(frame[pos.y][pos.x], pixel.tpl()):
		if time.time() > tEnd:
			fn(**fnArgs)
			tEnd = time.time() + delay
		frame = getframe(vid)


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


def checkShinyDialog(ser: serial.Serial, vid: cv2.VideoCapture, dialogPos: Pos, dialogColor: Pixel, delay: float = 2.0) -> tuple[ReturnCode, numpy.ndarray]:
	awaitPixel(ser, vid, pos=dialogPos, pixel=dialogColor)
	print(f"dialog start{PAD}\r", end="")

	encounterFrame = getframe(vid)

	crashed = False
	crashed |= not awaitNotPixel(ser, vid, pos=dialogPos, pixel=dialogColor)
	print(f"dialog end{PAD}\r", end="")
	t0 = time.time()

	crashed |= not awaitPixel(ser, vid, pos=dialogPos, pixel=dialogColor)
	t1 = time.time()

	diff = t1 - t0
	print(f"dialog delay: {diff:.3f}s{PAD}")

	waitAndRender(vid, 0.5)

	if diff >= 89 or crashed is True:
		raise RunCrash

	return (ReturnCode.SHINY if 10 > diff > delay else ReturnCode.OK, encounterFrame)


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

	config = loadJson("./config.json")
	serialPort = config.get("serialPort", "COM0")

	print(f"start encounters: {encounters}")

	try:
		with serial.Serial(serialPort, 9600) as ser, shh(ser):
			for e in mainFn(encounters, ser):
				encounters = e
	except (KeyboardInterrupt, RunStop):
		print("\033c", end="")
	except serial.SerialException as e:
		print(f"failed to open serial connection: {e}", file=sys.stderr)
	finally:
		cv2.destroyAllWindows()
		dumpJson(jsonPath, jsn | { encountersKey: encounters})
		print(f"saved encounters.. ({encounters}){PAD}\n")

	return 0


def _mainRunner(serialPort: str, encountersStart: int, fn: MAINRUNNER_FUNCTION, fnArgs: dict[str, Any]) -> int:
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

		sendMsg("Script started")
		try:
			while True:
				print("\033c", end="")

				runDelta = datetime.now() - tStart
				avg = runDelta / (currentEncounters if currentEncounters != 0 else 1)

				# remove microseconds so they don't show up as "0:12:34.567890"
				runDelta = timedelta(days=runDelta.days, seconds=runDelta.seconds)
				avg = timedelta(days=avg.days, seconds=avg.seconds)

				print(f"running for:  {runDelta} (average per reset: {avg})")
				print(f"encounters:   ({currentEncounters:>03}/{(encounters):>05})")
				print(f"crashes:      {crashes}\n")

				try:
					encounters, code, encounterFrame = fn(ser, vid, encounters, **fnArgs)
				except RunCrash:
					press(ser, vid, "A")
					waitAndRender(vid, 1)
					press(ser, vid, "A")
					crashes += 1
					continue

				if code == ReturnCode.CRASH:
					press(ser, vid, "A")
					waitAndRender(vid, 1)
					press(ser, vid, "A")
					crashes += 1
					continue
				elif code == ReturnCode.SHINY:
					sendMsg("Found a SHINY!!")

					scrName = f"tempScreenshot{uuid.uuid4()}.png"
					cv2.imwrite(scrName, encounterFrame)
					sendImg(scrName)
					os.remove(scrName)

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
						cmd = input("continue? (y/n) ").strip().lower()
						if cmd in ("y", "yes"):
							break
						elif cmd in ("n", "no"):
							raise RunStop
						else:
							print(f"invalid command: {cmd}", file=sys.stderr)
				elif code == ReturnCode.OK:
					if CFG_SEND_ALL_ENCOUNTERS is True:
						scrName = f"tempScreenshot{uuid.uuid4()}.png"
						cv2.imwrite(scrName, encounterFrame)
						sendImg(scrName)
						os.remove(scrName)
					currentEncounters += 1
				else:
					print(f"got invalid return code: {code}", sys.stderr)
		except (KeyboardInterrupt, EOFError):
			pass
		finally:
			vid.release()
			cv2.destroyAllWindows()
			return encounters


def mainRunner2(jsonPath: str, encountersKey: str, mainFn: MAINRUNNER_FUNCTION, parser: Optional[argparse.ArgumentParser] = None) -> int:
	global CFG_NOTIFY
	global CFG_RENDER
	global CFG_SEND_ALL_ENCOUNTERS

	if parser is None:
		parser = argparse.ArgumentParser()

	assert isinstance(parser, argparse.ArgumentParser)

	parser.add_argument("-R", "--disable-render", action="store_false", dest="render", help="disable rendering")
	parser.add_argument("-E", "--send-all-encounters", action="store_true", dest="sendEncounters", help="send a screenshot of all encounters")
	parser.add_argument("-n", "--notify", action="store_true", dest="notify", help="send notifications over telegram (requires telegram-send to be set up)")

	args = parser.parse_args().__dict__

	CFG_NOTIFY = bool(args.get("notify"))
	CFG_RENDER = bool(args.get("render"))
	CFG_SEND_ALL_ENCOUNTERS = bool(args.get("sendEncounters"))

	jsn, encounters = jsonGetDefault(
		loadJson(jsonPath),
		encountersKey,
		0,
	)

	config = loadJson("./config.json")
	serialPort = config.get("serialPort", "COM0")

	print(f"start encounters: {encounters}")

	try:
		encounters = _mainRunner(serialPort, encounters, mainFn, args)
	except RunStop:
		print("\033c", end="")
	except Exception as e:
		s = f"Program crashed: {e}"
		print(s, file=sys.stderr)
		sendMsg(s)
		raise
	else:
		print("\033c", end="")
	finally:
		dumpJson(jsonPath, jsn | { encountersKey: encounters})
		print(f"saved encounters.. ({encounters}){PAD}\n")

	return 0
