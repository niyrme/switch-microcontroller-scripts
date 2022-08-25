import logging
from typing import Optional

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import OWN_POKEMON_POS


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Shaymin",)

	@property
	def target(self) -> str:
		return "Shaymin"

	def getName(self) -> Optional[str]:
		return "Shaymin"

	def main(self, e: int) -> tuple[int, Frame]:
		self.press(Button.BUTTON_A)
		self.waitAndRender(3)
		self.press(Button.BUTTON_A)
		self.waitAndRender(2.5)

		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		encounterFrame = self.checkShinyDialog(e, 1.5)

		self.whileNotColor(OWN_POKEMON_POS, Color.White(), 0.5, lambda: self.press(Button.BUTTON_B))
		self.waitAndRender(1)

		self.runFromEncounter()

		self.press(Button.BUTTON_A)
		self.waitAndRender(0.5)

		logging.debug("reload area")
		self.press(Button.L_DOWN, 3.5)
		self.press(Button.L_UP, 3.8)
		return (e + 1, encounterFrame)
