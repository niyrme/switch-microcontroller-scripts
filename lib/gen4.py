import numpy

from lib import COLOR_BLACK
from lib import LOADING_SCREEN_POS
from lib import PAD
from lib import Pos
from lib import RunCrash
from lib import Script


ENCOUNTER_DIALOG_POS = Pos(670, 430)
SHORT_DIALOG_POS = Pos(560, 455)
OWN_POKEMON_POS = Pos(5, 425)


class Gen4Script(Script):
	def awaitInGame(self) -> None:
		crashed = not self.awaitPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("startup screen", PAD)

		crashed |= not self.awaitNotPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("after startup", PAD)

		if crashed is True:
			raise RunCrash

		# in splash screen
		self.waitAndRender(1)
		self.press("A")
		self.waitAndRender(3)
		self.press("A")
		self.waitAndRender(3)

		# loading screen to game
		crashed |= not self.awaitPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("loading screen", PAD)
		crashed |= not self.awaitNotPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)

		if crashed is True:
			raise RunCrash

		print("in game", PAD)
		self.waitAndRender(1)

	def awaitInGameSpam(self) -> None:
		self.awaitPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("startup screen", PAD)

		self.whilePixel(LOADING_SCREEN_POS, COLOR_BLACK, 0.5, lambda: self.press("A"))
		print("after startup", PAD)

		self.waitAndRender(1)

		frame = self.getframe()
		if numpy.array_equal(frame[LOADING_SCREEN_POS.y][LOADING_SCREEN_POS.x], (41, 41, 41)):
			raise RunCrash

		self.press("A")
		self.waitAndRender(3)

		# loading screen to game
		crashed = not self.awaitPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)
		print("loading screen", PAD)
		crashed |= not self.awaitNotPixel(pos=LOADING_SCREEN_POS, pixel=COLOR_BLACK)

		if crashed is True:
			raise RunCrash

		print("in game", PAD)
		self.waitAndRender(1)
