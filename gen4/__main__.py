import argparse
import sys
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
from .cresselia import CresseliaScript
from .darkrai import DarkraiScript
from .legendary import LegendaryScript
from .pixie import PixieScript
from .random import RandomScript
from .shaymin import ShayminScript
from .starter import StarterScript
from lib import Config
from lib import jsonGetDefault
from lib import PAD
from lib import ReturnCode
from lib import Script


def _main(args: dict[str, Any], encountersStart: int, scriptClass: Type[Script]) -> int:
	configJSON: dict[str, Union[str, bool]] = lib.loadJson(str(args["configFile"]))

	config = Config(
		str(configJSON.get("serialPort", "COM0")),
		bool(configJSON.get("notifyShiny", False)),
		bool(configJSON.get("renderCapture", True)),
		bool(configJSON.get("sendAllEncounters", False)),
		bool(configJSON.get("catchCrashes", False)),
		bool(configJSON.get("showLastRunDuration", False)),
	)

	print("Config:", PAD)
	print(config, "\n")

	print(f"start encounters: {encountersStart}")

	with serial.Serial(config.serialPort, 9600) as ser, lib.shh(ser):
		print("setting up cv2. This may take a while...")
		vid: cv2.VideoCapture = cv2.VideoCapture(0)
		vid.set(cv2.CAP_PROP_FPS, 30)
		vid.set(cv2.CAP_PROP_FRAME_WIDTH, 768)
		vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

		ser.write(b"0")
		time.sleep(0.1)

		currentEncounters = 0
		encounters = encountersStart
		crashes = 0

		script = scriptClass(ser, vid, config, **args)
		script.sendMsg("Script started")
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
					encounters, code, encounterFrame = script.main(encounters)
				except lib.RunCrash:
					if script.config.catchCrashes is True:
						print("\a")
						script.sendMsg("script crashed!")
						try:
							while True:
								script.waitAndRender(5)
						except KeyboardInterrupt:
							pass
					for _ in range(3):
						script.press("A")
						script.waitAndRender(1.5)
					crashes += 1
					continue
				finally:
					currentEncounters += 1

				runDuration = datetime.now() - runStart

				if code == ReturnCode.CRASH:
					script.press("A")
					script.waitAndRender(1)
					script.press("A")
					crashes += 1
					continue
				elif code == ReturnCode.SHINY:
					script.sendMsg("Found a SHINY!!")

					script.sendScreenshot(encounterFrame)

					ser.write(b"0")
					print("SHINY!!")
					print("SHINY!!")
					print("SHINY!!")
					print("\a")

					try:
						while True:
							if time.time() % 5 == 0:
								print("\a")
							script.getframe()
					except KeyboardInterrupt:
						pass

					while True:
						cmd = input("continue? (y/n) ").strip().lower()
						if cmd in ("y", "yes"):
							break
						elif cmd in ("n", "no"):
							raise lib.RunStop
						else:
							print(f"invalid command: {cmd}", file=sys.stderr)
				elif code == ReturnCode.OK:
					if script.config.sendAllEncounters is True:
						script.sendScreenshot(encounterFrame)
				else:
					print(f"got invalid return code: {code}", file=sys.stderr)
		except (KeyboardInterrupt, EOFError):
			pass
		finally:
			ser.write(b"0")
			vid.release()
			cv2.destroyAllWindows()
			return encounters


def main() -> int:
	# main parser for general arguments
	parser = argparse.ArgumentParser(prog="gen4", description="main runner for running scripts")
	parser.add_argument("-c", "--configFile", type=str, dest="configFile", default="config.json", help="configuration file (defualt: %(default)s)")
	parser.add_argument("-e", "--encounterFile", type=str, dest="encounterFile", default="shinyGrind.json", help="configuration file (defualt: %(default)s)")

	# parsers for each script
	scriptParser = parser.add_subparsers(dest="script")
	scriptParser.add_parser("cresselia", description="reset Cresselia")
	scriptParser.add_parser("darkrai", description="reset Darkrai")
	scriptParser.add_parser("legendary", description="reset Dialga/Palkia")
	scriptParser.add_parser("pixie", description="reset Uxie/Azelf")
	scriptParser.add_parser("shaymin", description="reset Shaymin")

	randomScriptParser = scriptParser.add_parser("random", description="reset random encounters")
	randomScriptParser.add_argument("direction", type=str, choices={"h", "v"}, help="direction to run in {(h)orizontal, (v)ertical} direction")
	randomScriptParser.add_argument("delay", type=float, help="delay betweeen changing direction")

	starterScriptParser = scriptParser.add_parser("starter", description="reset starter")
	starterScriptParser.add_argument("starter", type=int, choices={1, 2, 3}, help="which starter to reset (1: Turtwig, 2: Chimchar, 3: Piplup)")

	args = parser.parse_args().__dict__

	scriptName = args["script"]

	scripts: dict[str, Type[Script]] = {
		"cresselia": CresseliaScript,
		"darkrai": DarkraiScript,
		"legendary": LegendaryScript,
		"pixie": PixieScript,
		"shaymin": ShayminScript,
		"random": RandomScript,
		"starter": StarterScript,
	}

	jsn, encounters = jsonGetDefault(
		lib.loadJson(str(args["encounterFile"])),
		scriptName,
		0,
	)

	script = scripts[scriptName]
	assert script is not None

	try:
		encounters = _main(args, encounters, script)
	except lib.RunStop:
		print("\033c", end="")
	except Exception as e:
		print(f"Program crashed: {e}", file=sys.stderr)
		try:
			telegram_send.send(messages=(f"Program crashed: {e}",))
		except telegram.error.NetworkError as ne:
			print(f"telegram_send: connection failed: {ne}", file=sys.stderr)
		raise
	else:
		print("\033c", end="")
	finally:
		if script.storeEncounters is True:
			lib.dumpJson(str(args["encounterFile"]), jsn | {scriptName: encounters})
			print(f"saved encounters.. ({encounters}){PAD}\n")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
