import argparse
import time
from typing import Any
from typing import Optional

import serial

from lib import Button
from lib import Capture
from lib import Color
from lib import ExecStop
from lib import Frame
from lib import Pos
from lib import RequirementsAction
from lib.pokemon.sv import SVScript


_Requirements: tuple[str, ...] = ()
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)
Parser.add_argument("eggcount", type=int, choices=(1, 2, 3, 4, 5), help="amount of eggs to hatch")


dialogPositions = (Pos(500, 370), Pos(280, 400))
dialogColor = Color(3, 28, 35)


class Script(SVScript):
	def __init__(self, ser: serial.Serial, cap: Capture, config: dict[str, Any], **kwargs) -> None:
		super().__init__(ser, cap, config, **kwargs)

		self.count: int = kwargs.pop("eggcount")

		self.logInfo(f"Hatching {self.count} eggs")

	@property
	def target(self) -> str:
		return "Egg"

	def getName(self) -> Optional[str]:
		return "Egg"

	@property
	def extraStats(self) -> tuple[tuple[str, Any], ...]:
		return super().extraStats + (("Remaining eggs", self.count),)

	def main(self, e: int) -> tuple[int, Frame]:
		frame: Frame

		tEnd = time.time() + 30

		self._ser.write(Button.L_LEFT.encode())
		while True:
			frame = self.getframe()
			if all(frame.colorAt(pos) == dialogColor for pos in dialogPositions):
				break
			if time.time() > tEnd:
				self.press(Button.EMPTY)
				self._ser.write(Button.L_LEFT.encode())
				tEnd = time.time() + 30

		self.press(Button.EMPTY)

		# while True:
		# 	frame = self.getframe()
		# 	if all(frame.colorAt(pos) == dialogColor for pos in dialogPositions):
		# 		break
		# 	self.press(Button.L_LEFT, 3, render=True)

		self.logInfo("Egg hatching!")

		self.waitAndRender(1)

		self.press(Button.BUTTON_A)

		self.waitAndRender(15)

		self.press(Button.BUTTON_A)

		self.waitAndRender(5)

		self.count -= 1

		if self.count <= 0:
			raise ExecStop

		return (e, self.getframe())
