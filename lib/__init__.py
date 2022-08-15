import argparse
import contextlib
import json
import logging
import os
import time
import uuid
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Generator
from enum import Enum
from typing import Any
from typing import NamedTuple
from typing import Optional
from typing import TypeVar
from typing import Union

import cv2
import numpy
import serial
import telegram
import telegram_send


class ExecCrash(Exception):
	"""
	WIP

	Used when game crashes ("The software was closed because an error occured." screen)
	"""


class ExecLock(Exception):
	"""
	Used when the game "locks"

	(timeout on pixel detection, etc.)
	"""

	def __init__(self, ctx: Optional[str] = None, *args) -> None:
		super().__init__(*args)

		self.ctx = ctx


class ExecStop(Exception):
	"""Terminate script"""

	def __init__(self, encounters: Optional[int] = None, *args):
		super().__init__(*args)

		self.encounters = encounters


class Pos(NamedTuple):
	x: int
	y: int

	def __str__(self) -> str:
		return f"({self.x}, {self.y})"


class Pixel(NamedTuple):
	r: int
	g: int
	b: int

	@property
	def tpl(self) -> tuple[int, int, int]:
		return (self.r, self.g, self.b)

	def __str__(self) -> str:
		return f"({self.r}, {self.g}, {self.b})"


class Config(NamedTuple):
	serialPort: str
	lang: str
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
			f"   lang: {self.lang}",
			f"   {getMark(self.notifyShiny)} notify shiny encounters",
			f"   {getMark(self.renderCapture)} render captured video",
			f"   {getMark(self.sendAllEncounters)} send all encounters",
			f"   {getMark(self.catchCrashes)} catch game crashes",
			f"   {getMark(self.showLastRunDuration)} show last run duration",
		))


class Button(Enum):
	EMPTY = "0"
	BUTTON_A = "A"
	BUTTON_B = "B"
	BUTTON_X = "X"
	BUTTON_Y = "Y"
	BUTTON_HOME = "H"
	BUTTON_PLUS = "+"
	BUTTON_MINUS = "-"
	BUTTON_L = "L"
	BUTTON_R = "R"
	BUTTON_ZL = "l"
	BUTTON_ZR = "r"
	L_UP_LEFT = "q"
	L_UP = "w"
	L_UP_RIGHT = "e"
	L_LEFT = "a"
	L_RIGHT = "d"
	L_DOWN_LEFT = "z"
	L_DOWN_RIGHT = "c"
	L_DOWN = "s"
	R_UP_LEFT = "y"
	R_UP = "u"
	R_UP_RIGHT = "i"
	R_LEFT = "h"
	R_RIGHT = "k"
	R_DOWN_LEFT = "n"
	R_DOWN_RIGHT = "m"
	R_DOWN = "j"

	def encode(self) -> bytes:
		return str(self.value).encode()


PAD = " " * 32

COLOR_BLACK = Pixel(0, 0, 0)
COLOR_WHITE = Pixel(255, 255, 255)

LOADING_SCREEN_POS = Pos(705, 15)


@contextlib.contextmanager
def shh(ser: serial.Serial) -> Generator[None, None, None]:
	try: yield
	finally: ser.write(b'.')


def loadJson(filePath: str) -> dict:
	with open(filePath, "r+") as f:
		data: dict = json.load(f)
	return data


def dumpJson(filePath: str, data: dict) -> None:
	with open(filePath, "w") as f:
		json.dump(data, f, indent="\t", sort_keys=True)


T = TypeVar("T")
K = TypeVar("K")


def jsonGetDefault(data: dict[K, T], key: K, default: T) -> tuple[dict[K, T], T]:
	try:
		return (data, data[key])
	except KeyError:
		return (data | {key: default}, default)


class Capture:
	def __init__(self, *, width: int = 768, height: int = 480, fps: int = 30):
		self._vidWidth = width
		self._vidHeight = height

		vid = cv2.VideoCapture(0)
		vid.set(cv2.CAP_PROP_FPS, fps)
		vid.set(cv2.CAP_PROP_FRAME_WIDTH, width)
		vid.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

		self.vid: cv2.VideoCapture = vid

	@property
	def vidWidth(self) -> int:
		return self._vidWidth

	@property
	def vidHeight(self) -> int:
		return self._vidHeight

	def getFrame(self) -> numpy.ndarray:
		_, frame = self.vid.read()

		if cv2.waitKey(1) & 0xFF == ord("q"):
			raise SystemExit(0)

		return frame

	def getFrameRGB(self) -> numpy.ndarray:
		return cv2.cvtColor(self.getFrame(), cv2.COLOR_BGR2RGB)

	def __del__(self):
		if self.vid and self.vid.isOpened():
			self.vid.release()


class Script:
	storeEncounters: bool = True

	@staticmethod
	def parser(*args, **kwargs) -> argparse.ArgumentParser:
		parser = argparse.ArgumentParser(*args, **kwargs, add_help=False)
		parser.add_argument("-r", "--requirements", action="store_true", dest="getRequirements", help="print out the requirements for a script")
		return parser

	@staticmethod
	@abstractmethod
	def requirements() -> tuple[str, ...]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: Config, **kwargs) -> None:
		self._ser = ser
		self._cap = cap

		self.config: Config = config

		self.windowName: str = kwargs.pop("windowName", "Game")
		self.extraStats: list[tuple[str, Any]] = list()

	def __call__(self, e: int) -> Any:
		return self.main(e)

	@abstractmethod
	def main(self, e: int) -> Any:
		raise NotImplementedError

	def getframe(self) -> numpy.ndarray:
		frame = self._cap.getFrame()
		if self.config.renderCapture is True:
			cv2.imshow(self.windowName, frame)

		if cv2.waitKey(1) & 0xFF == ord("q"):
			raise ExecStop
		else:
			return frame

	def press(self, s: Union[str, Button], duration: float = 0.05, render: bool = False) -> None:
		logging.debug(f"press '{s}' for {duration}s")

		self._ser.write(s.encode())
		if render is True or duration >= 0.5:
			tEnd = time.time() + duration
			while time.time() < tEnd:
				self.getframe()
		else:
			time.sleep(duration)

		self._ser.write(b"0")
		time.sleep(0.075)

	def pressN(self, s: Union[str, Button], n: int, delay: float, duration: float = 0.05, render: bool = False) -> None:
		logging.debug(f"press '{s}' {n} times for {duration}s (delay: {delay}s)")

		for _ in range(n):
			self.press(s, duration, render)
			if render is True:
				self.waitAndRender(delay)
			else:
				time.sleep(delay)

	def waitAndRender(self, duration: float) -> None:
		logging.debug(f"wait for {duration}")
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

	def awaitPixel(self, pos: Pos, pixel: Pixel, timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time() + timeout
		while not numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
			if time.time() > tEnd:
				raise ExecLock(
					f"did not find color ({pixel}) at ({pos});"
					f"color in last frame: {frame[pos.y][pos.x]}",
				)
			frame = self.getframe()

	def awaitNotPixel(self, pos: Pos, pixel: Pixel, timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time() + timeout
		while numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
			if time.time() > tEnd:
				raise ExecLock(f"did not find not color ({pixel}) at ({pos})")
			frame = self.getframe()

	def awaitFlash(self, pos: Pos, pixel: Pixel, timeout: float = 90) -> None:
		self.awaitPixel(pos, pixel, timeout)
		self.awaitNotPixel(pos, pixel, timeout)

	def awaitNearPixel(self, pos: Pos, pixel: Pixel, distance: int = 30, timeout: float = 90) -> None:
		tEnd = time.time() + timeout
		frame = self.getframe()
		while not self.nearColor(frame[pos.y][pos.x], pixel, distance):
			if time.time() > tEnd:
				raise ExecLock(
					f"did not find near color ({pixel}) at ({pos}) (distance: {distance});"
					f"color in last frame: {frame[pos.y][pos.x]} (distance: {sum((c2 - c1) ** 2 for c1, c2 in zip(frame[pos.y][pos.x], pixel.tpl))})",
				)
			frame = self.getframe()

	def awaitNotNearPixel(self, pos: Pos, pixel: Pixel, distance: int = 30, timeout: float = 90) -> None:
		tEnd = time.time() + timeout
		frame = self.getframe()
		while self.nearColor(frame[pos.y][pos.x], pixel, distance):
			if time.time() > tEnd:
				raise ExecLock(
					f"did not find not near color ({pixel}) at ({pos}) (distance: {distance});"
					f"color in last frame: {frame[pos.y][pos.x]} (distance: {sum((c2 - c1) ** 2 for c1, c2 in zip(frame[pos.y][pos.x], pixel.tpl))})",
				)
			frame = self.getframe()

	def whilePixel(self, pos: Pos, pixel: Pixel, delay: float, fn: Callable[[], None], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				raise ExecLock(
					f"did not find color ({pixel}) at ({pos});"
					f"color in last frame: {frame[pos.y][pos.x]}",
				)
			frame = self.getframe()

	def whileNotPixel(self, pos: Pos, pixel: Pixel, delay: float, fn: Callable[[], None], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while not numpy.array_equal(frame[pos.y][pos.x], pixel.tpl):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				raise ExecLock(f"did not find not color ({pixel}) at ({pos})")
			frame = self.getframe()

	def whileNearPixel(self, pos: Pos, pixel: Pixel, distance: int, delay: float, fn: Callable[[], None], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while self.nearColor(frame[pos.y][pos.x], pixel, distance):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				raise ExecLock(
					f"did not find near color ({pixel}) at ({pos}) (distance: {distance});"
					f" color in last frame: {frame[pos.y][pos.x]} (distance: {sum((c2 - c1) ** 2 for c1, c2 in zip(frame[pos.y][pos.x], pixel.tpl))})",
				)
			frame = self.getframe()

	def whileNotNearPixel(self, pos: Pos, pixel: Pixel, distance: int, delay: float, fn: Callable[[], None], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while not self.nearColor(frame[pos.y][pos.x], pixel, distance):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				raise ExecLock(
					f"did not find not near color ({pixel}) as ({pos}) (distance: {distance});"
					f" color in last frame: {frame[pos.y][pos.x]} (distance: {sum((c2 - c1) ** 2 for c1, c2 in zip(frame[pos.y][pos.x], pixel.tpl))})",
				)
			frame = self.getframe()

	def resetGame(self) -> None:
		logging.debug("reset game")
		self.press(Button.BUTTON_HOME)
		self.waitAndRender(2)
		self.press(Button.BUTTON_X)
		self.waitAndRender(1)
		self.press(Button.BUTTON_A)
		self.waitAndRender(3)
		self.press(Button.BUTTON_A)
		self.waitAndRender(1)
		self.press(Button.BUTTON_A)
		self.waitAndRender(1)
		self.press(Button.BUTTON_A)

	def _sendTelegram(self, **kwargs) -> None:
		if self.config.notifyShiny is True:
			try:
				telegram_send.send(**kwargs)
			except telegram.error.NetworkError as e:
				logging.warning(f"telegram_send: connection failed: {e}")

	def sendMsg(self, msg: str) -> None:
		logging.debug(f"send telegram message: '{msg}'")
		self._sendTelegram(messages=(msg,))

	def sendImg(self, imgPath: str) -> None:
		with open(imgPath, "rb") as img:
			self._sendTelegram(images=(img,))

	def sendScreenshot(self, frame: numpy.ndarray) -> None:
		scrName = f"tempScreenshot{uuid.uuid4()}.png"
		cv2.imwrite(scrName, frame)
		self.sendImg(scrName)
		os.remove(scrName)
