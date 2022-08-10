import argparse
import importlib
import logging
import os
import time
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Type
from typing import Union

import cv2
import serial
import telegram
import telegram_send

import lib
from lib import Button
from lib import Config
from lib import jsonGetDefault
from lib.pokemon import ExecShiny
from lib.pokemon import LOG_DELAY
from lib.pokemon.bdsp import BDSPScript


TPokemonScript = Type[BDSPScript]


def _main(args: dict[str, Any], encountersStart: int, scriptClass: TPokemonScript) -> int:
	configJSON: dict[str, Union[str, bool]] = lib.loadJson(str(args.pop("configFile")))

	config = Config(
		serialPort=str(configJSON.pop("serialPort", "COM0")),
		lang=str(configJSON.pop("lang", "en")),
		notifyShiny=bool(configJSON.pop("notifyShiny", False)),
		renderCapture=bool(configJSON.pop("renderCapture", True)),
		sendAllEncounters=bool(configJSON.pop("sendAllEncounters", False)),
		catchCrashes=bool(configJSON.pop("catchCrashes", False)),
		showLastRunDuration=bool(configJSON.pop("showLastRunDuration", False)),
	)

	logging.info(f"start encounters: {encountersStart}")

	with serial.Serial(config.serialPort, 9600) as ser, lib.shh(ser):
		logging.info("setting up cv2. This may take a while...")
		vid: cv2.VideoCapture = cv2.VideoCapture(0)
		vid.set(cv2.CAP_PROP_FPS, 30)
		vid.set(cv2.CAP_PROP_FRAME_WIDTH, 768)
		vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

		ser.write(b"0")
		time.sleep(0.1)

		currentEncounters = 0
		encounters = encountersStart
		crashes = 0

		script = scriptClass(ser, vid, config, **args, windowName=f"Pokermans: {str(args['script']).capitalize()}")
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
					if script.config.sendAllEncounters is True:
						logging.debug("send screenshot")
						script.sendScreenshot(encounterFrame)
				finally:
					currentEncounters += 1
		except (KeyboardInterrupt, EOFError, lib.ExecStop):
			logging.info("script stopped")
		except Exception as e:
			s = f"Program crashed: {e}"
			script.sendMsg(s)
			logging.error(s)
		finally:
			ser.write(b"0")
			vid.release()
			cv2.destroyAllWindows()
			return encounters

	raise AssertionError("unreachable")


def main() -> int:
	parser = argparse.ArgumentParser(prog="bdsp", description="main runner for running scripts")
	parser.add_argument("-d", "--debug", action="store_const", const=logging.DEBUG, default=logging.INFO, dest="debug", help="output debugging info")
	parser.add_argument("-s", "--shiny-dialog-delay", action="store_const", const=LOG_DELAY, default=logging.INFO, dest="shinyDelay", help="log dialog delay to file")
	parser.add_argument("-c", "--config-file", type=str, dest="configFile", default="config.json", help="configuration file (defualt: %(default)s)")
	parser.add_argument("-e", "--encounter-file", type=str, dest="encounterFile", default="shinyGrind.json", help="file in which encounters are stored (defualt: %(default)s)")

	scriptNames = tuple(
		s[:-3] for s in filter(
			lambda f: str(f).endswith(".py") and not str(f).startswith("_"),
			os.listdir(os.path.dirname(os.path.abspath(__file__))),
		)
	)

	parser.add_argument("script", choices=scriptNames)

	_args, rest = parser.parse_known_args()
	args = vars(_args)

	logging.root.setLevel(min(args[k] for k in ("debug", "shinyDelay")))

	logging.debug(f"setting log-level to {logging.getLevelName(logging.root.level)}")
	logging.debug(f"scripts: {', '.join(scriptNames)}")

	scriptName = args["script"]
	try:
		mod = importlib.import_module(f"pokemon.bdsp.{scriptName}")
	except ModuleNotFoundError as e:
		logging.critical(e)
		return 1

	try:
		script: TPokemonScript = mod.Script
	except AttributeError:
		logging.critical(f"failed to get script from '{scriptName}'")
		return 1

	assert script is not None

	jsn, encounters = jsonGetDefault(
		lib.loadJson(str(args["encounterFile"])),
		scriptName,
		0,
	)

	scriptArgs = vars(script.parser().parse_args(rest))

	logging.info(f"running script: {scriptName}")

	try:
		encounters = _main(args | scriptArgs, encounters, script)
	except Exception as e:
		logging.error(f"program crashed: {e}")
		try:
			telegram_send.send(messages=(f"Program crashed: {e}",))
		except telegram.error.NetworkError as ne:
			logging.error(f"telegram_send: connection failed: {ne}")
		raise
	finally:
		if script.storeEncounters is True:
			lib.dumpJson(str(args["encounterFile"]), jsn | {scriptName: encounters})
			logging.info(f"saved encounters.. ({encounters})")

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
