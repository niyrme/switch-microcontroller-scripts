import logging
import pathlib
from abc import abstractmethod
from typing import Any
from typing import Optional

import serial

from lib import Capture
from lib import Frame
from lib import Script


class ExecShiny(Exception):
	"""
	Found a shiny pokemon
	"""

	def __init__(self, encounter: int, encounterFrame: Frame, *args: object) -> None:
		super().__init__(*args)
		self.encounter = encounter
		self.encounterFrame = encounterFrame


NamesPath = pathlib.Path(__file__).parent / "names"
Langs = (lang.name[:-4] for lang in NamesPath.iterdir())


class PokemonScript(Script):
	@abstractmethod
	def main(self, e: int) -> tuple[int, Frame]:
		raise NotImplementedError

	@staticmethod
	@abstractmethod
	def requirements() -> tuple[str, ...]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: dict[str, Any], **kwargs) -> None:
		super().__init__(ser, cap, config, **kwargs)

		self.configPokemon: dict[str, Any] = config.pop("pokemon")
		self.notifyShiny: bool = self.configPokemon.pop("notifyShiny", False)

		tempLang: Optional[str] = kwargs.pop("tempLang", None)
		lang = tempLang or self.configPokemon.pop("lang")

		with open(f"{NamesPath}/{lang}.txt", "r") as f:
			self._names = set(f.readlines())
		self.logDebug(f"language used for text recognition: {lang}")

	@property
	@abstractmethod
	def target(self) -> str:
		raise NotImplementedError


LOG_DELAY = logging.INFO - 1

logging.addLevelName(LOG_DELAY, "DELAY")
