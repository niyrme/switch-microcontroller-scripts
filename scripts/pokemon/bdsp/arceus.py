import argparse
import logging
from typing import Optional

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript


_Requirements: tuple[str, ...] = ("Stand at the last step before the platform",)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)


class Script(BDSPScript):
	@property
	def target(self) -> str:
		return "Arceus"

	def getName(self) -> Optional[str]:
		return "Arceus"

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.L_UP, 0.3)

		logging.debug("wait for flash (BLACK)")
		self.awaitFlash(LOADING_SCREEN_POS, Color.Black(), 5)
		self.waitAndRender(10.5)

		self.press(Button.BUTTON_A)
		self.waitAndRender(10)

		return (e + 1, self.checkShinyDialog(e, 1))
