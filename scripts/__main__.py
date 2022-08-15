import argparse
import importlib
import logging
import os
import pathlib
import time
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Type

import cv2
import serial
import telegram
import telegram_send

import lib
from lib import Button
from lib import Capture
from lib import Config
from lib import Script
from lib.pokemon import ExecShiny
from lib.pokemon import LOG_DELAY
from lib.pokemon.bdsp import BDSPScript


def run(scriptClass: Type[Script], args: dict[str, Any], encountersStart: int) -> int:
	configJSON: dict = lib.loadJson(args.pop("configFile"))

	cfg = Config(
		serialPort=configJSON.pop("serialPort", "COM0"),
		lang=configJSON.pop("lang", "en"),
		notifyShiny=configJSON.pop("notifyShiny", False),
		renderCapture=configJSON.pop("renderCapture", True),
		sendAllEncounters=configJSON.pop("sendAllEncounters", False),
		catchCrashes=configJSON.pop("catchCrashes", False),
		showLastRunDuration=configJSON.pop("showLastRunDuration", False),
	)

	sendNth: int = args.pop("sendNth")

	logging.info(f"start encounters: {encountersStart}")

	with serial.Serial(cfg.serialPort, 9600) as ser, lib.shh(ser):
		logging.info("setting up cv2. This may take a while...")
		cap = Capture(
			width=768,
			height=480,
			fps=30,
		)

		ser.write(b"0")
		time.sleep(0.1)

		currentEncounters = 0
		encounters = encountersStart
		crashes = 0

		script = scriptClass(ser, cap, cfg, **args, windowName=f"Pokermans: {str(args['script']).capitalize()}")
		script.sendMsg("Script started")
		logging.info("script started")
		script.waitAndRender(1)
		try:
			tStart = datetime.now()
			runDuration = timedelta(days=0, seconds=0)

			while True:
				print("\033c", end="")

				runDelta = datetime.now() - tStart
				avg = runDelta / (currentEncounters if currentEncounters != 0 else 1)
				stats: list[tuple[str, Any]] = [
					("running for", timedelta(days=runDelta.days, seconds=runDelta.seconds)),
					("average per reset", timedelta(days=avg.days, seconds=avg.seconds)),
					("encounters", f"{currentEncounters:>03}/{encounters:>05}"),
					("crashes", crashes),
				]
				if script.config.showLastRunDuration is True:
					stats.append(("last run duration", timedelta(days=runDuration.days, seconds=runDuration.seconds)))
				stats += script.extraStats

				maxStatInfoLen = max(len(s[0]) for s in stats) + 1

				for (info, stat) in stats:
					print(f"{(info + ':').ljust(maxStatInfoLen)} {stat}")

				print()

				runStart = datetime.now()
				try:
					encounters, encounterFrame = script(encounters)
					runDuration = datetime.now() - runStart
				except lib.ExecLock as e:
					ctx = f" (context: {e.ctx})" if e.ctx is not None else ""
					msg = f"script locked up{ctx}"
					logging.warning(msg)
					script.sendMsg(msg)

					logging.warning("check switch status and press ctrl+c to continue")

					try:
						while True:
							script.waitAndRender(3)
					except KeyboardInterrupt:
						pass
					crashes += 1
					continue
				except lib.ExecCrash:
					logging.warning("script crashed, reset switch to home screen and press ctrl+c to continue")
					if script.config.catchCrashes is True:
						print("\a")
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
					encounters = shiny.encounter
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

					logging.info(msg)
					script.sendMsg(msg)

					script.sendScreenshot(shiny.encounterFrame)

					try:
						while True:
							script.waitAndRender(3)
					except KeyboardInterrupt:
						cmd = input("continue? (y/n)")
						if cmd.lower() in ("y", "yes"):
							continue
						else:
							raise lib.ExecStop
				else:
					if sendNth >= 2 and currentEncounters % sendNth == 0:
						logging.debug("send screenshot")
						script.sendScreenshot(encounterFrame)

					if script.config.sendAllEncounters is True:
						logging.debug("send screenshot")
						script.sendScreenshot(encounterFrame)
				finally:
					currentEncounters += 1
		except lib.ExecStop as e:
			if e.encounters is not None:
				encounters = e.encounters
		except (KeyboardInterrupt, EOFError):
			logging.info("script stopped")
		except Exception as e:
			s = f"Program crashed: {e}"
			script.sendMsg(s)
			logging.error(s)
		finally:
			ser.write(b"0")
			return encounters

	raise AssertionError("unreachable")


def main() -> int:
	parser = argparse.ArgumentParser(prog="switchScripts")
	parser.add_argument("-d", "--debug", action="store_const", const=logging.DEBUG, default=logging.INFO, dest="debug", help="output debugging info")
	parser.add_argument("-s", "--shiny-dialog-delay", action="store_const", const=LOG_DELAY, default=logging.INFO, dest="shinyDelay", help="log dialog delay to file")
	parser.add_argument("-c", "--config-file", type=str, dest="configFile", default="config.json", help="configuration file (defualt: %(default)s)")
	parser.add_argument("-e", "--encounter-file", type=str, dest="encounterFile", default="encounters.json", help="file in which encounters are stored (defualt: %(default)s)")
	parser.add_argument("-n", "--send-nth-encounter", type=int, dest="sendNth", action="store", default=0, help="send every Nth encounter (must be 2 or higher; otherwise ignored)")

	path = pathlib.Path(__file__)

	games = []

	for _game in path.parent.iterdir():
		if not _game.is_dir(): continue

		mods: list[tuple[str, tuple[str, ...]]] = []
		for _module in _game.iterdir():
			if not _module.is_dir(): continue

			scripts: tuple[str, ...] = tuple(
				map(
					lambda s: s.name[:-3],
					filter(
						lambda s: s.is_file() and not s.name.startswith("_") and s.name.endswith(".py"),
						_module.iterdir(),
					),
				),
			)

			if len(scripts) != 0:
				mods.append((_module.name, scripts))

		if len(mods) != 0:
			games.append((_game.name, tuple(mods)))

	modules: dict[str, Type[Script]] = {}

	# TODO maybe move up to only iterate once?
	if len(games) != 0:
		_gamesParsers = parser.add_subparsers(dest="game")

		for _gameName, _gameMods in games:
			assert len(_gameMods) != 0
			_gameParser = _gamesParsers.add_parser(_gameName)
			_modParsers = _gameParser.add_subparsers(dest="mod")

			for _modName, _scripts in _gameMods:
				assert len(_scripts) != 0

				_modParser = _modParsers.add_parser(_modName)
				_scriptParsers = _modParser.add_subparsers(dest="script")

				for _scriptName in _scripts:
					_sMod = f"scripts.{_gameName}.{_modName}.{_scriptName}"
					try:
						_script: Type[Script] = importlib.import_module(_sMod).Script
					except ModuleNotFoundError:
						logging.warning(f"Failed to import {_sMod}")
					except AttributeError:
						logging.warning(f"Failed to get Script from {_sMod}")
					else:
						_scriptParsers.add_parser(_scriptName, parents=[_script.parser()])
						modules[_sMod] = _script

	args = vars(parser.parse_args())

	logging.root.setLevel(min(args[k] for k in ("debug", "shinyDelay")))

	logging.debug(f"setting log-level to {logging.getLevelName(logging.root.level)}")

	Nth: int = args["sendNth"]

	if Nth >= 2:
		m = {
			1: "st",
			2: "nd",
			3: "rd",
		}.get(int(str(Nth)[-1]), "th")

		logging.info(f"sending screenshot of every {Nth}{m} encounter")

	gameName: str = args.pop("game")
	modName: str = args.pop("mod")
	scriptName: str = args["script"]

	logging.debug(f"Game:   {gameName}")
	logging.debug(f"Mod:    {modName}")
	logging.debug(f"Script: {scriptName}")

	moduleName = f"scripts.{gameName}.{modName}.{scriptName}"

	try:
		script = modules[moduleName]
	except KeyError:
		logging.critical(f"failed to get Script from {moduleName}")
		return 1

	if args.pop("getRequirements") is True:
		print("Requirements")
		print("\n".join(f"  - {req}" for req in script.requirements()), end="\n\n")
		return 0

	encounterFile = args.pop("encounterFile")

	jsn = lib.loadJson(encounterFile)

	gameJson = jsn.get(gameName, dict())
	modJson = gameJson.get(modName, dict())
	encounters = modJson.get(scriptName, 0)

	logging.info(f"Running script: {scriptName}")

	try:
		encounters = run(script, args, encounters)
	except Exception as e:
		logging.error(e)
		try:
			telegram_send.send(messages=(f"Program crashed: {e}",))
		except telegram.error.NetworkError as ne:
			logging.error(f"telegram_send: connection failed {ne}")
		raise
	finally:
		if script.storeEncounters is True:
			lib.dumpJson(encounterFile, jsn | {gameName: gameJson | {modName: modJson | {scriptName: encounters}}})
			logging.info(f"saved encounters: {encounters}")

		cv2.destroyAllWindows()

	return 0


if __name__ == "__main__":
	now = datetime.now()
	os.makedirs("logs", exist_ok=True)
	logging.basicConfig(
		format="%(asctime)s [%(levelname)s] %(message)s",
		level=logging.INFO,
		datefmt="%Y/%m/%d-%H:%M:%S",
		handlers=(
			logging.StreamHandler(),
			logging.FileHandler(f"logs/switchcontroller-({now.strftime('%Y-%m-%d')})-({now.strftime('%H-%M-%S')}).log", "w+"),
		),
	)

	raise SystemExit(main())
