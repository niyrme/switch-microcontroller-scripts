import argparse
import importlib
import logging
import pathlib
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Optional
from typing import Type

import lib
from lib import Button
from lib import Color
from lib import DB
from lib import LOADING_SCREEN_POS
from lib import log
from lib import Pos
from lib.pokemon import ExecShiny
from lib.pokemon import PokemonRunner
from lib.pokemon import RunnerAction
from lib.pokemon.bdsp import BDSPScript


_scripsPath = pathlib.Path(__file__).parent
_scripts = tuple(
	s.name[:-3] for s in filter(
		lambda p: p.is_file() and not p.name.startswith("_") and p.name.endswith(".py"),
		_scripsPath.iterdir(),
	)
)


Parser = argparse.ArgumentParser(add_help=False)
_ScriptsParser = Parser.add_subparsers(dest="script")
for script in _scripts:
	try:
		_p = importlib.import_module(f"scripts.pokemon.bdsp.{script}").Parser
	except ModuleNotFoundError:
		log(logging.WARNING, f"failed to import {script}")
	except AttributeError:
		log(logging.WARNING, f"failed to get Parser from {script}")
	else:
		_ScriptsParser.add_parser(script, parents=(_p,))


def _stripTD(delta: timedelta) -> timedelta:
	return timedelta(days=delta.days, seconds=delta.seconds)


class Runner(PokemonRunner):
	def __init__(self, scriptClass: Type[BDSPScript], args: dict[str, Any], db: DB) -> None:
		self.script: BDSPScript
		super().__init__(scriptClass, args, db)

		self.sendNth: int = args.pop("sendNth")

		encountersStart: int = self.db.getOrInsert(self.key, 0)

		stopAt: Optional[int] = args.pop("stopAt")
		if stopAt is not None:
			if stopAt <= encountersStart:
				stopAt = None
			else:
				log(logging.INFO, f"running until encounters reach {stopAt}")

		self.encountersTotal = encountersStart
		self.encountersCurrent = 0

		self.stopAt = stopAt

		self.scriptStart = datetime.now()

		self.crashes = 0
		self.lastDuration = timedelta(0, 0)

		self.runStart = datetime.now()

	def __del__(self) -> None:
		self.serial.close()

	@property
	def key(self) -> str:
		return f"pokemon.bdsp.{self.script.target.lower()}"

	@property
	def encounters(self) -> int:
		return self.encountersTotal

	def idle(self) -> None:
		self.script.waitAndRender(5)

	def run(self) -> None:
		self.runStart = datetime.now()
		self.encountersTotal, encFrame = self.script(self.encountersTotal)

		if (
			self.script.sendAllEncounters is True or (
				self.script.sendAllEncounters is False and
				self.sendNth >= 2 and
				self.encountersCurrent % self.sendNth == 0
			)
		):
			self.script.logDebug("send screenshot")
			self.script.sendScreenshot(encFrame)

	def runPost(self) -> None:
		self.lastDuration = datetime.now() - self.runStart
		self._runs.append(self.lastDuration)
		self.encountersCurrent += 1

		if self.stopAt is not None and self.encountersTotal >= self.stopAt:
			self.script.logInfo(f"reached target of {self.stopAt} encounters")
			raise lib.ExecStop(self.encountersTotal)

	def onCrash(self, crash: lib.ExecCrash) -> RunnerAction:
		self.crashes += 1

		self.script.log(logging.WARNING, "script crashed, reset state and press Ctrl+C to continue")
		self.script.sendMsg("Script crashed!")
		self.script.idle()

		self.script.waitAndRender(1)

		return RunnerAction.Continue

	def onLock(self, lock: lib.ExecLock) -> RunnerAction:
		self.crashes += 1

		frame = self.script.getframe()
		if all(
			frame.colorAt(Pos(x, y)).distance(Color.Black()) == 0
			for x, y in ((420, 69), (150, 100), (555, 111), (111, 333))
		) and sum(
			frame.colorAt(Pos(x, y)).distance(Color.White()) <= 75
			for x, y in ((360, 90), (360, 100), (370, 60), (376, 80), (376, 99))
		) >= 2:
			self.script.log(logging.WARNING, "Game crashed. Resolving..")
			self.script.press(Button.BUTTON_A)
			self.script.waitAndRender(1)
			self.script.whileNotColor(LOADING_SCREEN_POS, Color.Black(), 0.5, lambda: self.script.press(Button.BUTTON_A))
			return RunnerAction.Continue
		del frame

		ctx = f" (context: {lock.ctx})" if lock.ctx is not None else ""
		msg = f"script locked up{ctx}"

		self.script.sendMsg(msg)
		self.script.log(logging.WARNING, msg)
		self.script.log(logging.WARNING, "reset state and press Ctrl+C to continue")

		try:
			while True:
				self.script.waitAndRender(5)
		except KeyboardInterrupt:
			pass

		self.script.waitAndRender(1)

		return RunnerAction.Continue

	def onShiny(self, shiny: ExecShiny) -> RunnerAction:
		name = ("SHINY " + (self.script.getName() or "")).strip()

		msg = f"found a {name.strip()} after {self.encountersTotal} encounters!"

		print("\a")

		self.script._maxDelay = True
		self.script.logInfo(msg)
		self.script.sendMsg(msg)
		self.script.sendScreenshot(shiny.encounterFrame)

		self.encountersTotal = shiny.encounter
		try:
			print("Press Ctrl+C for further actions")
			while True:
				self.script.waitAndRender(5)
		except KeyboardInterrupt:
			if input("continue? (y/n)").strip().lower() not in ("y", "yes"):
				return RunnerAction.Stop
			else:
				return RunnerAction.Continue

	@property
	def stats(self) -> tuple[tuple[str, Any]]:
		now = datetime.now()
		runDuration = now - self.scriptStart

		if len(self.runs) != 0:
			avg = timedelta(seconds=sum(r.total_seconds() for r in self.runs) / len(self.runs))
		else:
			avg = timedelta(days=0, seconds=0)

		stats: list[tuple[str, Any]] = [
			("Target", self.script.target),
			("Running for", _stripTD(runDuration)),
			("Average per reset", _stripTD(avg)),
			("Encounters", f"{self.encountersCurrent:>04}/{self.encountersTotal:>05}"),
			("Crashes", self.crashes),
		]

		if self.stopAt is not None:
			remainingEncounters = self.stopAt - self.encountersTotal
			remainingTime = avg * remainingEncounters
			estEnd = now + remainingTime

			stats.extend((
				("Stop at", self.stopAt),
				("Remaining", remainingEncounters),
				("Est. time remaining", _stripTD(remainingTime)),
				("Est. end", estEnd.strftime("%Y/%m/%d - %H:%M:%S")),
			))

		if self.script.showLastRunDuration is True:
			stats.append(("Last run duration", _stripTD(self.lastDuration)))

		if self.script.showBnp is True:
			stats.append(("B(n, p)", f"{((1 - ((4095 / 4096) ** self.encountersTotal)) * 100):.2f}%"))

		stats.extend(self.script.extraStats)

		return tuple(stats)

	@property
	def runs(self) -> list[timedelta]:
		return self._runs
