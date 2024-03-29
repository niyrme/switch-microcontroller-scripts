import argparse
import importlib
import logging
import pathlib
from datetime import datetime
from typing import Any
from typing import Optional
from typing import Type

import cv2
import telegram
import telegram_send

import lib
from lib import Button
from lib import DB
from lib import log
from lib.pokemon import ExecShiny
from lib.pokemon import Langs
from lib.pokemon import LOG_DELAY
from lib.pokemon import PokemonRunner
from lib.pokemon import PokemonScript
from lib.pokemon import RunnerAction


Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-l", "--lang", action="store", choices=Langs, default=None, dest="tempLang", help="override lang for this run only (instead of using the one from config)")
Parser.add_argument("-s", "--shiny-dialog-delay", action="store_true", dest="shinyDelay", help="log dialog delay to file")
Parser.add_argument("-e", "--encounter-file", type=str, dest="encounterFile", default="encounters.json", help="file in which encounters are stored (defualt: %(default)s)")
Parser.add_argument("-n", "--send-nth-encounter", type=int, dest="sendNth", action="store", default=0, help="send every Nth encounter (must be 2 or higher; otherwise ignored)")
Parser.add_argument("-S", "--stop-at", type=int, dest="stopAt", action="store", metavar="STOP", default=None, help="reset until encounters reach {%(metavar)s}; does nothing if set below current encounters (takes priority over --run-n-times)")
Parser.add_argument("-A", "--auto-start", dest="autoStart", action="store_true", help="don't wait for Ctrl+C to start script")
_modsParser = Parser.add_subparsers(dest="mod")

for p in pathlib.Path(__file__).parent.iterdir():
	modName = p.name
	if not p.is_dir() or modName.startswith("_"):
		continue

	try:
		_parser: argparse.ArgumentParser = importlib.import_module(f"scripts.pokemon.{modName}._runner").Parser
	except ModuleNotFoundError:
		log(logging.WARNING, f"failed to import {modName}")
		raise
	except AttributeError:
		log(logging.WARNING, f"failed to get Parser from {modName}")
		raise
	else:
		_modsParser.add_parser(modName, parents=(_parser,))


def _printStats(stats: tuple[tuple[str, Any], ...]) -> None:
	maxStatLen = max(len(i) for i, _ in stats) + 2

	print("\033c", end="")
	for info, stat in stats:
		if isinstance(stat, float):
			stat = f"{stat:3f}"
		print(f"{(info + ':').ljust(maxStatLen)} {stat}")
	print()


def _run(runnerClass: Type[PokemonRunner], scriptClass: Type[PokemonScript], args: dict[str, Any], db: DB) -> None:
	runner = runnerClass(scriptClass, args, db)

	action: Optional[RunnerAction]

	if args.pop("autoStart") is False:
		print("Press Ctrl+C to start")
		try:
			runner.script.idle()
		except (lib.ExecStop, KeyboardInterrupt, EOFError):
			return

	log(logging.INFO, "script started")
	runner.script.sendMessage("Script started")

	runner._scriptStart = datetime.now()

	try:
		while True:
			action = None

			_printStats(runner.stats)

			try:
				runner.run()
			except lib.ExecCrash as _exCrash:
				action = runner.onCrash(_exCrash)
			except lib.ExecLock as _exLock:
				action = runner.onLock(_exLock)
			except ExecShiny as _exShiny:
				action = runner.onShiny(_exShiny)
			except (KeyboardInterrupt, EOFError):
				runner.script.press(Button.EMPTY)
				while True:
					if (cmd := input("What do? (c)ontinue / (s)top ").strip().lower()) == "c":
						action = RunnerAction.Continue
						break
					elif cmd == "s":
						action = RunnerAction.Stop
						break
					else:
						print(f"Invalid command: {cmd}")
			finally:
				runner.script._cap.stopCapture()
				runner.runPost()

			runner.db.set(runner.key, {"encounters": runner.encounters, "totalTime": runner.totalTime})

			if action == RunnerAction.Continue:
				continue
			elif action == RunnerAction.Stop:
				break
	except lib.ExecStop as stop:
		encounters: int = stop.encounters or runner.encounters
		runner.db.set(runner.key, {"encounters": encounters, "totalTime": runner.totalTime})
	finally:
		runner.script.press(Button.EMPTY)
		log(logging.INFO, f"saved encounters: {runner.db.get(f'{runner.key}.encounters')}")
		log(logging.INFO, "script stopped")

		del runner


def run(args: dict[str, Any]) -> int:
	modName: str = args["mod"]
	scriptName: str = args["script"]

	modulePath = f"scripts.pokemon.{modName}.{scriptName}"
	log(logging.DEBUG, f"{modulePath=}")

	if args.pop("shinyDelay") is True:
		logging.getLogger("INFO").setLevel(LOG_DELAY)

	if (nth := args["sendNth"]) >= 2:
		_n = str(nth)

		for (n, s) in ((("11", "12", "13"), "th"), ("1", "st"), ("2", "nd"), ("3", "rd")):
			if _n.endswith(n):
				m = s
				break
		else:
			m = "th"

		log(logging.INFO, f"sending screenshot of every {nth}{m} encounter")

	try:
		scriptClass = importlib.import_module(modulePath).Script
	except ModuleNotFoundError as e:
		log(logging.CRITICAL, f"failed to import {modulePath}: {e}")
		return 1
	except KeyError:
		log(logging.CRITICAL, f"failed to get Script from {modulePath}")
		return 1

	db = DB(args.pop("encounterFile"))

	log(logging.INFO, f"Running script: {scriptName}")

	runnerPath = f"scripts.pokemon.{args.pop('mod')}._runner"

	try:
		runnerClass: Type[PokemonRunner] = importlib.import_module(runnerPath).Runner
	except ModuleNotFoundError:
		log(logging.CRITICAL, f"Failed to get runner module from {runnerPath}")
		return 0
	except AttributeError:
		log(logging.CRITICAL, f"Failed to get Runner from {runnerPath}")
		return 0

	try:
		_run(runnerClass, scriptClass, args, db)
	except Exception as e:
		import traceback
		traceback.print_tb(None)
		log(logging.ERROR, f'error: "{e}"')
		try:
			telegram_send.send(messages=(f"Program crashed: {e}",))
		except telegram.error.NetworkError as ne:
			log(logging.ERROR, f"telegram_send: connection failed {ne}")
		raise
	finally:
		cv2.destroyAllWindows()

	return 0
