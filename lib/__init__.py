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
from typing import Any
from typing import Callable
from typing import final
from typing import TypeVar
from typing import Union

import cv2
import serial
import telegram
import telegram_send

from ._button import Button as Button
from ._capture import Capture as Capture
from ._color import Color as Color
from ._frame import Frame as Frame
from ._logging import log as log
from ._logging import LOG_PRESS as LOG_PRESS
from ._logging import LOGGERS as LOGGERS
from ._pos import LOADING_SCREEN_POS as LOADING_SCREEN_POS
from ._pos import Pos as Pos
from .exceptions import ExecCrash as ExecCrash
from .exceptions import ExecLock as ExecLock
from .exceptions import ExecStop as ExecStop


@contextlib.contextmanager
def shh(ser: serial.Serial) -> Generator[None, None, None]:
	try: yield
	finally: ser.write(b'.')


def loadJson(filePath: str) -> dict[str, Any]:
	with open(filePath, "r+") as f:
		data: dict[str, Any] = json.load(f)
	return data


def dumpJson(filePath: str, data: dict[Any, Any]) -> None:
	with open(filePath, "w") as f:
		json.dump(data, f, indent="\t", sort_keys=True)


T = TypeVar("T")
K = TypeVar("K")


class RequirementsAction(argparse.Action):
	def __init__(self, option_strings: Sequence[str], requirements: Sequence[str], **kwargs) -> None:
		self.requirements = requirements

		super().__init__(option_strings, **kwargs, nargs=0)

	def __call__(self, parser: argparse.ArgumentParser, *args, **kwargs) -> None:
		print("Requirements")
		print("\n".join(f"  - {req}" for req in self.requirements))

		parser.exit()


class Script:
	@staticmethod
	@abstractmethod
	def requirements() -> tuple[str, ...]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: dict[str, Any], **kwargs) -> None:
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

	@final
	def log(self, level: int, msg: str) -> None:
		log(level, msg)

	@final
	def logDebug(self, msg: str) -> None:
		self.log(logging.DEBUG, msg)

	@final
	def logInfo(self, msg: str) -> None:
		self.log(logging.INFO, msg)

	def getframe(self) -> Frame:
		frame = self._cap.read()

		if self.renderCapture is True:
			cv2.imshow(self.windowName, frame.ndarray)

		if cv2.waitKey(1) & 0xFF == ord("q"):
			raise ExecStop
		else:
			return frame

	def press(self, s: Union[str, Button], duration: float = 0.05, render: bool = False) -> None:
		self.log(LOG_PRESS, f"press '{s}' for {duration}s")

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
		self.log(LOG_PRESS, f"press '{s}' {n} times for {duration}s (delay: {delay}s)")

		for _ in range(n):
			self.press(s, duration, render)
			if render is True:
				self.waitAndRender(delay)
			else:
				time.sleep(delay)

	def waitAndRender(self, duration: float) -> None:
		self.logDebug(f"wait for {duration}")
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

	def awaitColors(self, colors: tuple[tuple[Pos, Color], ...], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time() + timeout

		while not all(map(lambda c: frame.colorAt(c[0]) == c[1], colors)):
			if time.time() > tEnd:
				raise ExecLock(f"did not find colors ({(f'{c} at {p}' for p, c in colors)})")
			frame = self.getframe()

	def awaitNotColors(self, colors: tuple[tuple[Pos, Color], ...], timeout: float = 90) -> None:
		frame = self.getframe()
		tEnd = time.time() + timeout

		while all(map(lambda c: frame.colorAt(c[0]) == c[1], colors)):
			if time.time() > tEnd:
				raise ExecLock
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
		self.logDebug("reset game")
		self.press(Button.BUTTON_HOME)
		self.waitAndRender(2)
		self.press(Button.BUTTON_X)
		self.waitAndRender(1)
		self.whileNotColor(LOADING_SCREEN_POS, Color.Black(), 0.5, lambda: self.press(Button.BUTTON_A))

	def _sendTelegram(self, **kwargs) -> None:
		try:
			telegram_send.send(**kwargs)
		except telegram.error.NetworkError as e:
			self.log(logging.WARNING, f"telegram_send: connection failed: {e}")

	def sendMsg(self, msg: str) -> None:
		self.logDebug(f"send telegram message: '{msg}'")
		self._sendTelegram(messages=(msg,))

	def sendScreenshot(self, frame: Frame) -> None:
		with tempfile.TemporaryDirectory() as tempDirName:
			p = f"{tempDirName}/screenshot.png"
			cv2.imwrite(p, frame.ndarray)
			with open(p, "rb") as img:
				self._sendTelegram(images=(img,))
