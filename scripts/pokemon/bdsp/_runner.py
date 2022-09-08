import argparse
import importlib
import logging
import pathlib
import threading
import time
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Optional
from typing import Type

import serial
import yaml

import lib
from lib import Button
from lib import Capture
from lib import log
from lib.pokemon import ExecShiny
from lib.pokemon import Langs
from lib.pokemon.bdsp import BDSPScript


_scripsPath = pathlib.Path(__file__).parent
_scripts = tuple(
	map(
		lambda s: s.name[:-3],
		filter(
			lambda s: s.is_file() and not s.name.startswith("_") and s.name.endswith(".py"),
			_scripsPath.iterdir(),
		),
	),
)


Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-l", "--lang", action="store", choices=Langs, default=None, dest="tempLang", help="override lang for this run only (instead of using the one from config)")

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


def printStats(
	script: BDSPScript,
	scriptStart: datetime,
	crashes: int,
	encounters: tuple[int, int],
	stopAt: Optional[int],
	lastDuration: timedelta,
) -> None:
	now = datetime.now()
	runDuration = _stripTD(now - scriptStart)

	encCurrent, encTotoal = encounters

	avg = _stripTD(runDuration / (encCurrent or 1))

	stats: list[tuple[str, Any]] = [
		("Target", script.target),
		("Running for", runDuration),
		("Average per reset", avg),
		("Encounter", f"{encCurrent:>04}/{encTotoal:>05}"),
		("Crashes", crashes),
	]

	if stopAt is not None:
		remainingEncounters = stopAt - encTotoal
		remainingTime = _stripTD(avg * remainingEncounters)
		estEnd = scriptStart + remainingTime

		stats.extend((
			("Stop at", stopAt),
			("Remaining", remainingEncounters),
			("Est. time remaining", remainingTime),
			("Est. end", estEnd.strftime("%Y/%m/%d - %H:%M:%S")),
		))

	if script.showLastRunDuration is True:
		stats.append(("Last run duration", _stripTD(lastDuration)))

	if script.showBnp is True:
		bnp = (1 - ((4095 / 4096) ** encTotoal)) * 100
		stats.append(("B(n, p)", f"{bnp:.2f}%"))

	stats.extend(script.extraStats)

	maxStatLen = max(len(s[0]) for s in stats) + 2

	print("\033c", end="")
	for info, stat in stats:
		if isinstance(stat, float):
			stat = f"{stat:.3f}"
		print(f"{(info + ':').ljust(maxStatLen)} {stat}")


def run(scriptClass: Type[BDSPScript], args: dict[str, Any], encountersStart: int) -> int:
	log(logging.INFO, f"start encounters: {encountersStart}")
	with open(args.pop("configFile"), "r") as f:
		cfg: dict[str, Any] = yaml.safe_load(f)

	sendNth: int = args.pop("sendNth")

	stopAt: Optional[int] = args.pop("stopAt")
	if stopAt is not None:
		if stopAt <= encountersStart:
			stopAt = None
		else:
			log(logging.INFO, f"running until encounters reach {stopAt}")

	with serial.Serial(cfg.pop("serialPort", "COM0"), 9600) as ser, lib.shh(ser):
		log(logging.INFO, "setting up cv2. This may take a while...")
		cap = Capture(
			width=768,
			height=480,
			fps=30,
		)

		ser.write(b"0")
		time.sleep(0.1)

		encounters = encountersStart

		script = scriptClass(ser, cap, cfg, **args, windowName="Pokermans")
		script.sendMsg("Script started")
		log(logging.INFO, "script started")
		script.waitAndRender(1)

		crashes = 0
		currentEncounters = 0
		lastDuration = timedelta(0, 0)

		try:
			scriptStart = datetime.now()

			while True:
				printStats(script, scriptStart, crashes, (currentEncounters, encounters), stopAt, lastDuration)

				runStart = datetime.now()
				try:
					encounters, encounterFrame = script(encounters)
				except lib.ExecLock as e:
					ctx = f" (context: {e.ctx})" if e.ctx is not None else ""
					msg = f"script locked up{ctx}"
					script.log(logging.WARNING, msg)
					script.sendMsg(msg)

					script.log(logging.WARNING, "check switch status and press ctrl+c to continue")

					try:
						while True:
							script.waitAndRender(3)
					except KeyboardInterrupt:
						pass
					crashes += 1
					continue
				except lib.ExecCrash:
					script.log(logging.WARNING, "script crashed, reset switch to home screen and press ctrl+c to continue")
					script.sendMsg("script crashed!")
					try:
						while True:
							script.waitAndRender(5)
					except KeyboardInterrupt:
						pass
					script.waitAndRender(1)
					script.pressN(Button.BUTTON_A, 5, 1.5)
					crashes += 1
					continue
				except ExecShiny as shiny:
					if isinstance(script, BDSPScript):
						script.waitAndRender(15)
						name = script.getName()
						if name is not None:
							name = f"SHINY {name}"
						else:
							name = "SHINY"

						msg = f"found a {name}!"
					else:
						msg = "found a SHINY!"

					log(logging.INFO, msg)
					script.sendMsg(msg)

					script.sendScreenshot(shiny.encounterFrame)

					try:
						while True:
							script.waitAndRender(3)
					except KeyboardInterrupt:
						cmd = input("continue? (y/n)")
						if cmd.lower() not in ("y", "yes"):
							raise lib.ExecStop(shiny.encounter + 1)
				else:
					if script.sendAllEncounters is False and sendNth >= 2 and currentEncounters % sendNth == 0:
						log(logging.DEBUG, "send screenshot")
						script.sendScreenshot(encounterFrame)
					elif script.sendAllEncounters is True:
						log(logging.DEBUG, "send screenshot")
						script.sendScreenshot(encounterFrame)
				finally:
					currentEncounters += 1
					lastDuration = datetime.now() - runStart

					if stopAt is not None and encounters >= stopAt:
						log(logging.INFO, f"reached target of {stopAt} encounters")
						log(logging.INFO, "stoppping script")
						break
		except lib.ExecStop as e:
			if e.encounters is not None:
				encounters = e.encounters
			log(logging.INFO, "script stopped")
		except (KeyboardInterrupt, EOFError):
			log(logging.INFO, "script stopped")
		except Exception as e:
			s = f"Program crashed: {e}"
			script.sendMsg(s)
			log(logging.ERROR, s)
		finally:
			ser.write(b"0")
			return encounters

	raise AssertionError("unreachable")
