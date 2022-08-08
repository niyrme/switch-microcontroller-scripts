import numpy

from lib import ReturnCode
from lib.pokemon.bdsp import Gen4Script


class Script(Gen4Script):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		raise NotImplementedError("Arceus script is currently only a placeholder for the real thing later on")

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		raise NotImplementedError("Arceus script is currently only a placeholder for the real thing later on")
