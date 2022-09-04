from typing import Optional


class ExecCrash(Exception):
	"""
	WIP

	Used when game crashes ("The software was closed because an error occured." screen)
	"""


class ExecLock(Exception):
	"""
	Used when the game "locks"

	(timeout on pixel detection, etc.)
	"""

	def __init__(self, ctx: Optional[str] = None, *args) -> None:
		super().__init__(*args)

		self.ctx = ctx


class ExecStop(Exception):
	"""Terminate script"""

	def __init__(self, encounters: Optional[int] = None, *args):
		super().__init__(*args)

		self.encounters = encounters
