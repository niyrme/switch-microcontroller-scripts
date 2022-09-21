import argparse
from typing import Optional

import lib
from lib import Button
from lib import Color
from lib import Frame
from lib import Pos
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import SHORT_DIALOG_POS_1
from lib.pokemon.bdsp import SHORT_DIALOG_POS_2


_Requirements: tuple[str, ...] = ("Stand at the last step before the platform",)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)

_DIALOG_POS_COLS: tuple[tuple[Pos, Color], ...] = (
	(SHORT_DIALOG_POS_1, Color.White()),
	(SHORT_DIALOG_POS_2, Color.White()),
	(Pos(260, 450), Color.White()),
	(Pos(420, 420), Color.White()),
)


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

		self.logDebug("wait for dialog")
		try:
			print("waiting for text box")
			self.awaitColors(_DIALOG_POS_COLS)
		except lib.ExecLock:
			f = self.getframe()
			if not all(f.colorAt(p).distance(c) <= 32 for p, c in _DIALOG_POS_COLS):
				while True:
					if (do := input("continue here? (y/yes | n/no)").lower()) in ("y", "yes"):
						break
					elif do in ("n", "no"):
						raise

		self.waitAndRender(1.5)

		self.press(Button.BUTTON_A)
		self.waitAndRender(10)

		return (e + 1, self.checkShinyDialog(e, 1))
