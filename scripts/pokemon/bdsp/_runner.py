import logging
import time
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Type

import serial
import yaml

import lib
from lib import Button
from lib import Capture
from lib import Config
from lib.pokemon import ExecShiny
from lib.pokemon.bdsp import BDSPScript


def run(scriptClass: Type[BDSPScript], args: dict[str, Any], encountersStart: int) -> int:
	with open(args.pop("configFile"), "r") as f:
		cfg: Config = yaml.safe_load(f)

	sendNth: int = args.pop("sendNth")

	logging.info(f"start encounters: {encountersStart}")

	with serial.Serial(cfg.pop("serialPort", "COM0"), 9600) as ser, lib.shh(ser):
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

		script = scriptClass(ser, cap, cfg, **args, windowName="Pokermans")
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
					("Target", script.target),
					("Running for", timedelta(days=runDelta.days, seconds=runDelta.seconds)),
					("Average per reset", timedelta(days=avg.days, seconds=avg.seconds)),
					("Encounters", f"{currentEncounters:>03}/{encounters:>05}"),
					("Crashes", crashes),
				]
				if script.showLastRunDuration is True:
					stats.append(("Last run duration", timedelta(days=runDuration.days, seconds=runDuration.seconds)))
				if script.showBnp is True:
					bnp = (1 - ((4095 / 4096) ** encounters)) * 100
					stats.append(("B(n, p)", f"{bnp:.2f}%"))
				stats.extend(script.extraStats)

				maxStatInfoLen = max(len(s[0]) for s in stats) + 1
				for (info, stat) in stats:
					if isinstance(stat, float):
						stat = f"{stat:.3f}"
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

					logging.info(msg)
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
						logging.debug("send screenshot")
						script.sendScreenshot(encounterFrame)
					elif script.sendAllEncounters is True:
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
