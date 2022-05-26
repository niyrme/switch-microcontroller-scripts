import argparse
import contextlib
import json
import os
import sys
import time
import uuid
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Generator
from datetime import datetime
from enum import IntEnum
from typing import Any
from typing import NamedTuple
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

	@property
	def tpl(self) -> tuple[int, int, int]:
		return (self.r, self.g, self.b)


class ReturnCode(IntEnum):
	CRASH = -1
	OK = 0
	SHINY = 1


class Config(NamedTuple):
	serialPort: str
	notifyShiny: bool = False
	renderCapture: bool = True
	sendAllEncounters: bool = False
	catchCrashes: bool = False
	showLastRunDuration: bool = False

	def __str__(self) -> str:
		def getMark(b: bool) -> str:
			return "\u2705" if b is True else "\u274E"

		# works ¯\_(ツ)_/¯
		return "\n".join((
			f"   serial port: {self.serialPort}",
			f"   {getMark(self.notifyShiny)} notify shiny encounters",
			f"   {getMark(self.renderCapture)} render captured video",
			f"   {getMark(self.sendAllEncounters)} send all encounters",
			f"   {getMark(self.catchCrashes)} catch game crashes",
			f"   {getMark(self.showLastRunDuration)} show last run duration",
		))


PAD = " " * 32

COLOR_BLACK = Pixel(0, 0, 0)
COLOR_WHITE = Pixel(255, 255, 255)

LOADING_SCREEN_POS = Pos(705, 15)

CFG_NOTIFY: bool = False
CFG_RENDER: bool = True
CFG_SEND_ALL_ENCOUNTERS: bool = False
CFG_CATCH_CRASH: bool = False

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


def sendScreenshot(image: numpy.ndarray) -> None:
	scrName = f"tempScreenshot{uuid.uuid4()}.png"
	cv2.imwrite(scrName, image)
	sendImg(scrName)
	os.remove(scrName)


def alarm(ser: serial.Serial, vid: cv2.VideoCapture) -> None:
	for _ in range(3):
		ser.write(b"!")
		waitAndRender(vid, 1)
		ser.write(b".")
		waitAndRender(vid, 0.4)


def nearPixel(pixel: numpy.ndarray, expected: Pixel, distance: int = 75) -> bool:
	return sum(
		(c2 - c1) ** 2
		for c1, c2 in zip(pixel, expected.tpl)
	) < distance


def press(ser: serial.Serial, vid: cv2.VideoCapture, s: str, duration: float = .05) -> None:
	print(f"{datetime.now().strftime('%H:%M:%S')} '{s}' for {duration} {PAD}\r", end="")

	ser.write(s.encode())
	if duration >= 0.5:
		tEnd = time.time() + duration
		while time.time() < tEnd:
			getframe(vid)
	else:
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
	while not numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
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
	while numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
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
	fn: Callable[[], None],
) -> None:
	frame = getframe(vid)
	tEnd = time.time() + delay
	while numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
		if time.time() > tEnd:
			fn()
			tEnd = time.time() + delay
		frame = getframe(vid)


def whileNotPixel(
	ser: serial.Serial,
	vid: cv2.VideoCapture,
	pos: Pos,
	pixel: Pixel,
	delay: float,
	fn: Callable[[], None],
) -> None:
	frame = getframe(vid)
	tEnd = time.time() + delay
	while not numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
		if time.time() > tEnd:
			fn()
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

	crashed = False
	crashed |= not awaitNotPixel(ser, vid, pos=dialogPos, pixel=dialogColor)
	print(f"dialog end{PAD}\r", end="")
	t0 = time.time()

	encounterFrame = getframe(vid)
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
		return (data | {key: default}, default)


class Script:
	storeEncounters: bool = True
	scriptName: str

	@staticmethod
	def parser() -> argparse.ArgumentParser:
		return argparse.ArgumentParser(add_help=False)

	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		self._ser = ser
		self._vid = vid

		self.config: Config = config

		self.windowName: str = kwargs.get("windowName", "Game")
		self.extraStats: list[tuple[str, Any]] = list()

	@abstractmethod
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		raise NotImplementedError

	def getframe(self) -> numpy.ndarray:
		_, frame = self._vid.read()

		if self.config.renderCapture is True:
			cv2.imshow(self.windowName, frame)

		if cv2.waitKey(1) & 0xFF == ord("q"):
			raise RunStop
		else:
			return frame

	def press(self, s: str, duration: float = 0.05, render: bool = False) -> None:
		print(f"{datetime.now().strftime('%H:%M:%S')} '{s}' for {duration} {PAD}\r", end="")

		self._ser.write(s.encode())
		if render is True or duration >= 0.5:
			tEnd = time.time() + duration
			while time.time() < tEnd:
				self.getframe()
		else:
			time.sleep(duration)

		self._ser.write(b"0")
		time.sleep(0.075)

	def waitAndRender(self, duration: float) -> None:
		tEnd = time.time() + duration
		while time.time() < tEnd:
			self.getframe()

	def alarm(self) -> None:
		for _ in range(3):
			self._ser.write(b"!")
			self.waitAndRender(1)
			self._ser.write(b".")
			self.waitAndRender(0.4)

	def nearColor(self, pixel: numpy.ndarray, expected: Pixel, distance: int = 75) -> bool:
		d = sum(
			(c2 - c1) ** 2
			for c1, c2 in zip(pixel, expected.tpl)
		)
		return d < distance

	def awaitPixel(self, pos: Pos, pixel: Pixel, timeout: float = 90) -> bool:
		frame = self.getframe()
		tEnd = time.time() + timeout
		while not numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
			frame = self.getframe()
			if time.time() > tEnd:
				return False
		else:
			return True

	def awaitNotPixel(self, pos: Pos, pixel: Pixel, timeout: float = 90) -> bool:
		frame = self.getframe()
		tEnd = time.time() + timeout
		while numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
			frame = self.getframe()
			if time.time() > tEnd:
				return False
		else:
			return True

	def awaitFlash(self, pos: Pos, pixel: Pixel, timeout: float = 90) -> bool:
		if not self.awaitPixel(pos, pixel, timeout):
			return False
		else:
			return self.awaitNotPixel(pos, pixel, timeout)

	def awaitNearPixel(self, pos: Pos, pixel: Pixel, distance: int = 30, timeout: float = 90) -> bool:
		tEnd = time.time() + timeout
		frame = self.getframe()
		while not self.nearColor(frame[pos.y][pos.x], pixel, distance):
			frame = self.getframe()
			if time.time() > tEnd:
				return False
		else:
			return True

	def awaitNotNearPixel(self, pos: Pos, pixel: Pixel, distance: int = 30, timeout: float = 90) -> bool:
		tEnd = time.time() + timeout
		frame = self.getframe()
		while self.nearColor(frame[pos.y][pos.x], pixel, distance):
			frame = self.getframe()
			if time.time() > tEnd:
				return False
		else:
			return True

	def whilePixel(self, pos: Pos, pixel: Pixel, delay: float, fn: Callable[[], None], timeout: float = 90) -> bool:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				return False
			frame = self.getframe()

		return True

	def whileNotPixel(self, pos: Pos, pixel: Pixel, delay: float, fn: Callable[[], None], timeout: float = 90) -> bool:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while not numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				return False
			frame = self.getframe()

		return True

	def whileNearPixel(self, pos: Pos, pixel: Pixel, distance: int, delay: float, fn: Callable[[], None], timeout: float = 90) -> bool:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while self.nearColor(frame[pos.y][pos.x], pixel, distance):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				return False
			frame = self.getframe()

		return True

	def whileNotNearPixel(self, pos: Pos, pixel: Pixel, distance: int, delay: float, fn: Callable[[], None], timeout: float = 90) -> bool:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while not self.nearColor(frame[pos.y][pos.x], pixel, distance):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				return False
			frame = self.getframe()

		return True

	def resetGame(self) -> None:
		self.press("H")
		self.waitAndRender(1)
		self.press("X")
		self.waitAndRender(1)
		self.press("A")
		self.waitAndRender(3)
		self.press("A")
		self.waitAndRender(1)
		self.press("A")
		self.waitAndRender(1)
		self.press("A")

	def _sendTelegram(self, **kwargs) -> None:
		if self.config.notifyShiny is True:
			try:
				telegram_send.send(**kwargs)
			except telegram.error.NetworkError as e:
				print(f"telegram_send: connection failed: {e}", file=sys.stderr)

	def sendMsg(self, msg: str) -> None:
		self._sendTelegram(messages=(msg,))

	def sendImg(self, imgPath: str) -> None:
		with open(imgPath, "rb") as img:
			self._sendTelegram(images=(img,))

	def sendScreenshot(self, frame: numpy.ndarray) -> None:
		scrName = f"tempScreenshot{uuid.uuid4()}.png"
		cv2.imwrite(scrName, frame)
		self.sendImg(scrName)
		os.remove(scrName)
