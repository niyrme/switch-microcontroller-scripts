from abc import abstractmethod
from typing import Any

import serial

from . import PokemonScript
from lib import Capture
from lib import Frame
from lib import ScriptT


class SVScript(PokemonScript[ScriptT]):
	@abstractmethod
	def main(self, e: int) -> tuple[int, Frame]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: dict[str, Any], **kwargs) -> None:
		super().__init__(ser, cap, config, **kwargs)

	@property
	@abstractmethod
	def target(self) -> str:
		raise NotImplementedError
