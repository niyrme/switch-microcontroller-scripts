import logging

from lib import Frame


class ExecShiny(Exception):
	"""
	Found a shiny pokemon
	"""

	def __init__(self, encounter: int, encounterFrame: Frame, *args: object) -> None:
		super().__init__(*args)
		self.encounter = encounter
		self.encounterFrame = encounterFrame


LOG_DELAY = logging.INFO - 1

logging._levelToName.update({LOG_DELAY: "DELAY"})
logging._nameToLevel.update({"DELAY": LOG_DELAY})
