import logging
import pathlib
from abc import abstractmethod
from datetime import datetime
from enum import IntEnum
from typing import Any
from typing import Final
from typing import final
from typing import Optional
from typing import Type

import serial
import yaml

from lib import Capture
from lib import DB
from lib import ExecCrash
from lib import ExecLock
from lib import Frame
from lib import log
from lib import Script


@final
class ExecShiny(Exception):
	"""
	Found a shiny pokemon
	"""

	def __init__(self, encounter: int, encounterFrame: Frame, *args: object) -> None:
		super().__init__(*args)
		self.encounter = encounter
		self.encounterFrame = encounterFrame


NamesPath: Final[pathlib.Path] = pathlib.Path(__file__).parent / "names"
global Langs
Langs: Final[tuple[str, ...]] = tuple(lang.name[:-4] for lang in NamesPath.iterdir())

LOG_DELAY: Final[int] = logging.INFO - 1
logging.addLevelName(LOG_DELAY, "DELAY")


class PokemonScript(Script):
	@abstractmethod
	def main(self, e: int) -> tuple[int, Frame]:
		raise NotImplementedError

	def __init__(self, ser: serial.Serial, cap: Capture, config: dict[str, Any], **kwargs) -> None:
		super().__init__(ser, cap, config, **kwargs)

		self.configPokemon: Final[dict[str, Any]] = config.pop("pokemon")
		self.notifyShiny: Final[bool] = self.configPokemon.pop("notifyShiny", False)

		tempLang: Optional[str] = kwargs.pop("tempLang", None)
		lang: str = tempLang or self.configPokemon.pop("lang")

		with open(f"{NamesPath}/{lang}.txt", "r") as f:
			self._names: Final[set[str]] = set(f.readlines())
		self.logDebug(f"language used for text recognition: {lang}")

	@property
	@abstractmethod
	def target(self) -> str:
		raise NotImplementedError


@final
class RunnerAction(IntEnum):
	Stop = 0
	Continue = 1


class PokemonRunner:
	def __init__(self, scriptClass: Type[PokemonScript], args: dict[str, Any], db: DB) -> None:
		with open(args.pop("configFile"), "r") as fp:
			cfg: dict[str, Any] = yaml.safe_load(fp)

		self.db: Final[DB] = db
		self.serial: Final[serial.Serial] = serial.Serial(cfg.pop("serialPort", "COM0"), 9600)

		self.script: PokemonScript = self._setup(scriptClass, cfg, args)

		self._runs: Final[list[float]] = []

		self._scriptStart = datetime.now()

	def _setup(self, scriptClass: Type[PokemonScript], config: dict[str, Any], args: dict[str, Any]) -> PokemonScript:
		log(logging.INFO, "setting up cv2. This may take a while...")
		cap = Capture(width=768, height=480, fps=30)

		return scriptClass(self.serial, cap, config, **args, windowName="Pokermans")

	def __del__(self):
		self.serial.close()

	@final
	def __call__(self) -> None:
		self.run()

	@final
	@property
	def scriptStart(self) -> datetime:
		return self._scriptStart

	@final
	@property
	def target(self) -> str:
		return self.script.target

	@property
	@abstractmethod
	def totalTime(self) -> float:
		raise NotImplementedError

	@property
	@abstractmethod
	def key(self) -> str:
		raise NotImplementedError

	@abstractmethod
	def idle(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def run(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def runPost(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def onCrash(self, crash: ExecCrash) -> RunnerAction:
		raise NotImplementedError

	@abstractmethod
	def onLock(self, lock: ExecLock) -> RunnerAction:
		raise NotImplementedError

	@abstractmethod
	def onShiny(self, shiny: ExecShiny) -> RunnerAction:
		raise NotImplementedError

	@property
	@abstractmethod
	def encounters(self) -> int:
		raise NotImplementedError

	@property
	@abstractmethod
	def stats(self) -> tuple[tuple[str, Any], ...]:
		raise NotImplementedError

	@final
	@property
	def runs(self) -> list[float]:
		return self._runs
