from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib.pokemon.bdsp import BDSPScript


class Script(BDSPScript):
	@staticmethod
	def requirements() -> tuple[str, ...]:
		return ("Stand in front of Dialga/Palkia",)

	@property
	def target(self) -> str:
		return "Dialga/Palkia"

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		# walk towards legendary
		self.press(Button.L_UP, duration=0.5)
		self.waitAndRender(2)
		self.pressN(Button.BUTTON_B, 3, 0.5, render=True)

		# flash to enter battle
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		# flash inside battle
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		# encounter dialog
		return (e + 1, self.checkShinyDialog(e, 1.5))
