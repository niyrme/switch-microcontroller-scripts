import argparse
import sys
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
from .cresselia import CresseliaScript
from .legendary import LegendaryScript
from .pixie import PixieScript
from .random import RandomScript
from .shaymin import ShayminScript
from .starter import StarterScript
from lib import jsonGetDefault
from lib import PAD
from lib import ReturnCode
from lib import Script


def _main(serialPort: str, encountersStart: int, scriptClass: Type[Script], scriptArgs: dict[str, Any]) -> int:
	with serial.Serial(serialPort, 9600) as ser, lib.shh(ser):
		print("setting up cv2. This may take a while...")
		vid: cv2.VideoCapture = cv2.VideoCapture(0)
		vid.set(cv2.CAP_PROP_FPS, 30)
		vid.set(cv2.CAP_PROP_FRAME_WIDTH, 768)
		vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

		ser.write(b"0")
		time.sleep(0.1)

		tStart = datetime.now()
		currentEncounters = 0
		encounters = encountersStart
		crashes = 0

		script = scriptClass(ser, vid, **scriptArgs)
		script.sendMsg("Script started")
		script.waitAndRender(1)
		try:
			while True:
				print("\033c", end="")

				runDelta = datetime.now() - tStart
				avg = runDelta / (currentEncounters if currentEncounters != 0 else 1)

				# remove microseconds so they don't show up as "0:12:34.567890"
				runDelta = timedelta(days=runDelta.days, seconds=runDelta.seconds)
				avg = timedelta(days=avg.days, seconds=avg.seconds)

				print(f"running for:  {runDelta} (average per reset: {avg})")
				print(f"encounters:   ({currentEncounters:>03}/{(encounters):>05})")
				print(f"crashes:      {crashes}\n")

				try:
					encounters, code, encounterFrame = script.main(encounters)
				except lib.RunCrash:
					if script.CFG_CATCH_CRASH is True:
						print("\a")
						script.sendMsg("script crashed!")
						try:
							while True:
								script.waitAndRender(5)
						except KeyboardInterrupt:
							pass
					script.press("A")
					script.waitAndRender(1)
					script.press("A")
					crashes += 1
					continue

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
					currentEncounters += 1
					if script.CFG_SEND_ALL_ENCOUNTERS is True:
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
	parser.add_argument("-R", "--disable-render", action="store_false", dest="CFG_RENDER", help="disable rendering")
	parser.add_argument("-E", "--send-all-encounters", action="store_true", dest="CFG_SEND_ALL_ENCOUNTERS", help="send a screenshot of all encounters")
	parser.add_argument("-n", "--notify", action="store_true", dest="CFG_NOTIFY", help="send notifications over telegram (requires telegram-send to be set up)")
	parser.add_argument("-C", "--catch-crash", action="store_true", dest="CFG_CATCH_CRASH", help="pause program if game crashed")

	# parsers for each script
	scriptParser = parser.add_subparsers(dest="script")
	scriptParser.add_parser("cresselia")
	scriptParser.add_parser("legendary")
	scriptParser.add_parser("pixie")
	scriptParser.add_parser("shaymin")

	eggHatchScriptPatser = scriptParser.add_parser("eggHatch")
	eggHatchScriptPatser.add_argument("direction", type=str, choices={"h", "v"}, help="direction to run in {(h)orizontal, (v)ertical} direction")
	eggHatchScriptPatser.add_argument("delay", type=float, help="delay betweeen changing direction")
	eggHatchScriptPatser.add_argument("eggCount", type=int, help="number of eggs to hatch")

	randomScriptParser = scriptParser.add_parser("random")
	randomScriptParser.add_argument("direction", type=str, choices={"h", "v"}, help="direction to run in {(h)orizontal, (v)ertical} direction")
	randomScriptParser.add_argument("delay", type=float, help="delay betweeen changing direction")

	starterScriptParser = scriptParser.add_parser("starter")
	starterScriptParser.add_argument("starter", type=int, choices={1, 2, 3}, help="which starter to reset (1: Turtwig, 2: Chimchar, 3: Piplup)")

	args = parser.parse_args().__dict__

	scriptName = args["script"]

	scripts: dict[str, Type[Script]] = {
		"cresselia": CresseliaScript,
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

	def getMark(b: bool) -> str:
		return "\u2705" if b is True else "\u274E"

	configJSON = lib.loadJson(str(args["configFile"]))
	serialPort = configJSON.get("serialPort", "COM0")

	print("Config:", PAD)
	print(f"   Serial Port: '{serialPort}'")
	print(f"   {getMark(args['CFG_RENDER'])} Render")
	print(f"   {getMark(args['CFG_NOTIFY'])} Notify Telegram")
	print(f"   {getMark(args['CFG_SEND_ALL_ENCOUNTERS'] & args['CFG_NOTIFY'])} Send All Encounters")
	print(f"   {getMark(args['CFG_CATCH_CRASH'])} Catch Crashes\n")

	script = scripts[scriptName]
	assert script is not None

	if script.storeEncounters is True:
		print(f"start encounters: {encounters}")

	try:
		encounters = _main(serialPort, encounters, script, args)
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
