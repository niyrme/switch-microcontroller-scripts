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

import lib
from lib import Button
from lib import Capture
from lib import Config
from lib import Script
from lib.pokemon import ExecShiny
from lib.pokemon import LOG_DELAY
from lib.pokemon.bdsp import BDSPScript


def _main(scriptClass: Type[Script], args: dict[str, Any], restArgs: tuple[str, ...], encountersStart: int) -> int:
	scriptArgs = vars(scriptClass.parser().parse_args(restArgs))
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

		script = scriptClass(ser, cap, cfg, **scriptArgs, windowName=f"Pokermans: {str(args['script']).capitalize()}")
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
		for module in _game.iterdir():
			if not module.is_dir(): continue

			scripts: tuple[str, ...] = tuple(
				map(
					lambda s: s.name[:-3],
					filter(
						lambda s: s.is_file() and not s.name.startswith("_") and s.name.endswith(".py"),
						module.iterdir(),
					),
				),
			)

			if len(scripts) != 0:
				mods.append((module.name, scripts))

		if len(mods) != 0:
			games.append((_game.name, tuple(mods)))

	if len(games) != 0:
		gamesParsers = parser.add_subparsers(dest="game")

		for gameName, gameMods in games:
			assert len(gameMods) != 0
			gameParser = gamesParsers.add_parser(gameName)

			gameParserS = gameParser.add_subparsers(dest="mod")

			for modName, scripts in gameMods:
				assert len(scripts) != 0

				modParser = gameParserS.add_parser(modName)
				modParser.add_argument("script", action="store", type=str, choices=scripts)

	_args, rest = parser.parse_known_args()
	args: dict[str, Any] = vars(_args)

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

	logging.debug(f"Game:   {args['game']}")
	logging.debug(f"Mod:    {args['mod']}")
	logging.debug(f"Script: {args['script']}")

	gameName: str = args["game"]
	modName: str = args["mod"]
	scriptName: str = args["script"]

	moduleName = f"{gameName}.{modName}.{scriptName}"

	try:
		impModule = importlib.import_module(moduleName)
	except ModuleNotFoundError as e:
		logging.critical(e)
		return 1

	try:
		script: Type[Script] = impModule.Script
	except AttributeError:
		logging.critical(f"failed to import script from {moduleName}")
		return 1

	jsn = lib.loadJson(args["encounterFile"])

	try:
		gameJson = jsn[gameName]
	except KeyError:
		jsn[gameName] = {}
		gameJson = {}

	try:
		modJson = gameJson[modName]
	except KeyError:
		gameJson[modName] = {}
		modJson = {}

	try:
		encounters = modJson[scriptName]
	except KeyError:
		encounters = 0

	try:
		encounters = _main(script, args, tuple(rest), encounters)
	except Exception as e:
		logging.error(e)
	finally:
		if script.storeEncounters is True:
			lib.dumpJson(args["encounterFile"], jsn | {gameName: gameJson | {modName: modJson | {scriptName: encounters}}})
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
