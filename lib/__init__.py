from __future__ import annotations

import argparse
import contextlib
import json
import logging
import tempfile
import time
from abc import abstractmethod
from collections.abc import Generator
from collections.abc import Sequence
from enum import Enum
from typing import Any
from typing import Callable
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


class Color(NamedTuple):
	r: int
	g: int
	b: int

	@property
	def tpl(self) -> tuple[int, int, int]:
		return (self.r, self.g, self.b)

	@staticmethod
	def White() -> Color:
		return Color(255, 255, 255)

	@staticmethod
	def Black() -> Color:
		return Color(0, 0, 0)

	def __str__(self) -> str:
		return f"({self.r}, {self.g}, {self.b})"

	def distance(self, other: Color) -> int:
		return sum(
			(c2 - c1) ** 2
			for c1, c2 in zip(self.tpl, other.tpl)
		)


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


class Frame:
	def __init__(self, frame: numpy.ndarray) -> None:
		self._frame = frame

	@property
	def ndarray(self) -> numpy.ndarray:
		return self._frame

	def colorAt(self, pos: Pos) -> Color:
		b, g, r = self._frame[pos.y][pos.x]
		return Color(r, g, b)


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

	def read(self) -> Frame:
		_, frame = self.vid.read()

		return Frame(frame)

	def getFrameRGB(self) -> numpy.ndarray:
		return cv2.cvtColor(self.read().ndarray, cv2.COLOR_BGR2RGB)

	def __del__(self):
		if self.vid and self.vid.isOpened():
			self.vid.release()


class RequirementsAction(argparse.Action):
	def __init__(self, option_strings: Sequence[str], requirements: Sequence[str], **kwargs) -> None:
		self.requirements = requirements

		super().__init__(option_strings, **kwargs, nargs=0)

	def __call__(self, parser: argparse.ArgumentParser, *args, **kwargs) -> None:
		print("Requirements")
		print("\n".join(f"  - {req}" for req in self.requirements))

		parser.exit()


Config = dict[str, Any]


class Script:
	@staticmethod
	@abstractmethod
	def requirements() -> tuple[str, ...]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: Config, **kwargs) -> None:
		self._ser = ser
		self._cap = cap

		self.windowName: str = kwargs.pop("windowName", "Game")

		self.renderCapture: bool = config.pop("renderCapture", True)

	def __call__(self, e: int) -> Any:
		return self.main(e)

	@property
	def extraStats(self) -> tuple[tuple[str, Any], ...]:
		return tuple()

	@abstractmethod
	def main(self, e: int) -> Any:
		raise NotImplementedError

	def getframe(self) -> Frame:
		frame = self._cap.read()

		if self.renderCapture is True:
			cv2.imshow(self.windowName, frame.ndarray)

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

	def nearColor(self, current: Color, expected: Color, distance: int = 75) -> bool:
		return current.distance(expected) <= distance

	def awaitColor(self, pos: Pos, color: Color, timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time() + timeout
		while frame.colorAt(pos) != color:
			if time.time() > tEnd:
				raise ExecLock(
					f"did not find color ({color}) at ({pos});"
					f"color in last frame: {frame.colorAt(pos)}",
				)
			frame = self.getframe()

	def awaitNotColor(self, pos: Pos, color: Color, timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time() + timeout
		while frame.colorAt(pos) == color:
			if time.time() > tEnd:
				raise ExecLock(f"did not find not color ({color}) at ({pos})")
			frame = self.getframe()

	def awaitFlash(self, pos: Pos, color: Color, timeout: float = 90) -> None:
		self.awaitColor(pos, color, timeout)
		self.awaitNotColor(pos, color, timeout)

	def awaitNearColor(self, pos: Pos, color: Color, distance: int = 30, timeout: float = 90) -> None:
		tEnd = time.time() + timeout
		frame = self.getframe()
		while not self.nearColor(frame.colorAt(pos), color, distance):
			if time.time() > tEnd:
				raise ExecLock(
					f"did not find near color ({color}) at ({pos}) (distance: {distance});"
					f"color in last frame: {frame.colorAt(pos)} (distance: {frame.colorAt(pos).distance(color)})",
				)
			frame = self.getframe()

	def awaitNotNearColor(self, pos: Pos, color: Color, distance: int = 30, timeout: float = 90) -> None:
		tEnd = time.time() + timeout
		frame = self.getframe()
		while self.nearColor(frame.colorAt(pos), color, distance):
			if time.time() > tEnd:
				raise ExecLock(
					f"did not find not near color ({color}) at ({pos}) (distance: {distance});"
					f"color in last frame: {frame.colorAt(pos)} (distance: {frame.colorAt(pos).distance(color)})",
				)
			frame = self.getframe()

	def whileColor(self, pos: Pos, color: Color, delay: float, fn: Callable[[], None], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while frame.colorAt(pos) == color.tpl:
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				raise ExecLock(
					f"did not find color ({color}) at ({pos});"
					f"color in last frame: {frame.colorAt(pos)}",
				)
			frame = self.getframe()

	def whileNotColor(self, pos: Pos, color: Color, delay: float, fn: Callable[[], None], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while frame.colorAt(pos) != color.tpl:
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				raise ExecLock(f"did not find not color ({color}) at ({pos})")
			frame = self.getframe()

	def whileNearColor(self, pos: Pos, color: Color, distance: int, delay: float, fn: Callable[[], None], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while self.nearColor(frame.colorAt(pos), color, distance):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				raise ExecLock(
					f"did not find near color ({color}) at ({pos}) (distance: {distance});"
					f" color in last frame: {frame.colorAt(pos)} (distance: {sum((c2 - c1) ** 2 for c1, c2 in zip(frame.colorAt(pos), color.tpl))})",
				)
			frame = self.getframe()

	def whileNotNearColor(self, pos: Pos, color: Color, distance: int, delay: float, fn: Callable[[], None], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time()
		tStop = time.time() + timeout
		while not self.nearColor(frame.colorAt(pos), color, distance):
			t = time.time()
			if t > tEnd:
				fn()
				tEnd = time.time() + delay
			elif t > tStop:
				raise ExecLock(
					f"did not find not near color ({color}) as ({pos}) (distance: {distance});"
					f" color in last frame: {frame.colorAt(pos)} (distance: {sum((c2 - c1) ** 2 for c1, c2 in zip(frame.colorAt(pos), color.tpl))})",
				)
			frame = self.getframe()

	def resetGame(self) -> None:
		logging.debug("reset game")
		self.press(Button.BUTTON_HOME)
		self.waitAndRender(2)
		self.press(Button.BUTTON_X)
		self.waitAndRender(1)
		self.whileNotColor(LOADING_SCREEN_POS, Color.Black(), 0.5, lambda: self.press(Button.BUTTON_A))

	def _sendTelegram(self, **kwargs) -> None:
		try:
			telegram_send.send(**kwargs)
		except telegram.error.NetworkError as e:
			logging.warning(f"telegram_send: connection failed: {e}")

	def sendMsg(self, msg: str) -> None:
		logging.debug(f"send telegram message: '{msg}'")
		self._sendTelegram(messages=(msg,))

	def sendScreenshot(self, frame: Frame) -> None:
		with tempfile.TemporaryDirectory() as tempDirName:
			p = f"{tempDirName}/screenshot.png"
			cv2.imwrite(p, frame.ndarray)
			with open(p, "rb") as img:
				self._sendTelegram(images=(img,))
