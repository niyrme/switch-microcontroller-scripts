import numpy

from lib import ReturnCode
from lib import Script
from lib.gen4 import awaitInGameSpam


class CresseliaScript(Script):
	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		self.resetGame()
		awaitInGameSpam(self._ser, self._vid)

		raise NotImplementedError
