import argparse
import importlib
import logging
import pathlib
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Final
from typing import final
from typing import Type

import lib
from lib import DB
from lib import Frame
from lib import log
from lib.pokemon import ExecShiny
from lib.pokemon import PokemonRunner
from lib.pokemon import RunnerAction
from lib.pokemon.sv import SVScript


_scriptsPath = pathlib.Path(__file__).parent
_scripts = (
	s.name[:-3] for s in filter(
		lambda p: p.is_file() and p.name.endswith(".py") and not p.name.startswith("_"),
		_scriptsPath.iterdir(),
	)
)


Parser = argparse.ArgumentParser(add_help=False)
_ScriptsParser = Parser.add_subparsers(dest="script")
for script in _scripts:
	try:
		_p: argparse.ArgumentParser = importlib.import_module(f"scripts.pokemon.sv.{script}").Parser
	except ModuleNotFoundError:
		log(logging.WARNING, f"failed to import {script}")
		raise
	except AttributeError:
		log(logging.WARNING, f"failed to get Parser from {script}")
		raise
	else:
		_ScriptsParser.add_parser(script, parents=(_p,))


def _stripTD(delta: timedelta) -> timedelta:
	return timedelta(days=delta.days, seconds=delta.seconds)


@final
class Runner(PokemonRunner):
	def __init__(self, scriptClass: Type[SVScript], args: dict[str, Any], db: DB) -> None:
		self.script: SVScript[tuple[int, Frame]]
		super().__init__(scriptClass, args, db)

		self._target: Final[str] = self.script.target

		stat: dict[str, Any] = self.db.getOrInsert(self.key, {"encounters": 0, "totalTime": 0})

		self._totalTime = stat.pop("totalTime")

		self.encountersTotal = stat.pop("encounters")
		self.encountersCurrent = 0

		self.crashes = 0

		self.lastRunDuration = timedelta(0, 0)
		self.runStart = datetime.now()

	@property
	def key(self) -> str:
		return f"pokemon.sv.{self._target.lower()}"

	@property
	def totalTime(self) -> int:
		return self._totalTime

	def idle(self) -> None:
		self.script.waitAndRender(5)

	def run(self) -> None:
		self.runStart = datetime.now()
		self.encountersTotal, _ = self.script(self.encountersTotal)

		# TODO

	def runPost(self) -> None:
		# TODO
		self.lastRunDuration = datetime.now() - self.runStart
		self._runs.append(self.lastRunDuration.total_seconds())
		self.encountersCurrent += 1

	def onCrash(self, crash: lib.ExecCrash) -> RunnerAction:
		# TODO
		raise NotImplementedError

	def onLock(self, lock: lib.ExecLock) -> RunnerAction:
		# TODO
		raise NotImplementedError

	def onShiny(self, shiny: ExecShiny) -> RunnerAction:
		# TODO
		raise NotImplementedError

	@property
	def encounters(self) -> int:
		return self.encountersTotal

	@property
	def stats(self) -> tuple[tuple[str, Any], ...]:
		now = datetime.now()
		runDuration = now - self.scriptStart

		avg = timedelta(seconds=sum(self.runs) / (len(self.runs) or 1))

		stats: list[tuple[str, Any]] = [
			("Target", self._target),
			("Total runtime", _stripTD(timedelta(seconds=self.totalTime))),
			("Running for", _stripTD(runDuration)),
			("Average per reset", _stripTD(avg)),
			("Encounters", f"{self.encountersCurrent:>04}/{self.encountersTotal:>05}"),
			("Crashes", self.crashes),
		]

		# if self.script.showLastRunDuration is True:
		# 	stats.append(("Last run duration", _stripTD(self.lastRunDuration)))

		stats.extend(self.script.extraStats)

		return tuple(stats)
