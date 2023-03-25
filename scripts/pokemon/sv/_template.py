import argparse

from lib import Frame
from lib import RequirementsAction
from lib.pokemon.sv import SVScript


_Requirements: tuple[str, ...] = ()
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)


class Script(SVScript):
	@property
	def target(self) -> str:
		raise NotImplementedError

	def main(self, e: int) -> tuple[int, Frame]:
		raise NotImplementedError
