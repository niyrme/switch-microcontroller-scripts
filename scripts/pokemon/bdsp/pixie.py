import argparse

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript


_Requirements: tuple[str, ...] = ("Stand in front of Azelf/Uxie",)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)


class Script(BDSPScript):
	@property
	def target(self) -> str:
		return "Azelf/Uxie"

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)
		self.press(Button.BUTTON_A)
		self.waitAndRender(2.5)

		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		# encounter dialog
		return (e + 1, self.checkShinyDialog(e, 1.5))
