import argparse
import importlib
import logging
from typing import Any
from typing import Type

import cv2
import telegram
import telegram_send

import lib
from .bdsp._runner import Parser as ParserBDSP
from lib import log
from lib.pokemon import Langs
from lib.pokemon import LOG_DELAY
from lib.pokemon import PokemonScript


Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-l", "--lang", action="store", choices=Langs, default=None, dest="tempLang", help="override lang for this run only (instead of using the one from config)")
Parser.add_argument("-s", "--shiny-dialog-delay", action="store_true", dest="shinyDelay", help="log dialog delay to file")
Parser.add_argument("-e", "--encounter-file", type=str, dest="encounterFile", default="encounters.json", help="file in which encounters are stored (defualt: %(default)s)")
Parser.add_argument("-n", "--send-nth-encounter", type=int, dest="sendNth", action="store", default=0, help="send every Nth encounter (must be 2 or higher; otherwise ignored)")
Parser.add_argument("-S", "--stop-at", type=int, dest="stopAt", action="store", metavar="STOP", default=None, help="reset until encounters reach {%(metavar)s}; does nothing if set below current encounters (takes priority over --run-n-times)")
Parser.add_subparsers(dest="mod").add_parser("bdsp", parents=(ParserBDSP,))


def _run(scriptClass: Type[PokemonScript], args: dict[str, Any], encountersStart: int) -> int:
	modName = args.pop("mod")

	runnerPath = f"scripts.pokemon.{modName}._runner"
	try:
		return importlib.import_module(runnerPath).run(scriptClass, args, encountersStart)
	except ModuleNotFoundError:
		log(logging.CRITICAL, f"Failed to get runner module from {runnerPath}")
	except AttributeError:
		log(logging.CRITICAL, f"Failed to get runner function from {runnerPath}")

	return encountersStart


def run(args: dict[str, Any]) -> int:
	modName: str = args["mod"]
	scriptName: str = args["script"]

	modulePath = f"scripts.pokemon.{modName}.{scriptName}"
	log(logging.DEBUG, f"{modulePath=}")

	if args.pop("shinyDelay") is True:
		logging.getLogger("INFO").setLevel(LOG_DELAY)

	try:
		script = importlib.import_module(modulePath).Script
	except ModuleNotFoundError as e:
		log(logging.CRITICAL, f"failed to import {modulePath}: {e}")
		return 1
	except KeyError:
		log(logging.CRITICAL, f"failed to get Script from {modulePath}")
		return 1

	encounterFile = args.pop("encounterFile")

	jsn = lib.loadJson(encounterFile)

	gameJson = jsn.get("pokemon", dict())
	modJson = gameJson.get(modName, dict())
	encounters = modJson.get(scriptName, 0)

	log(logging.INFO, f"Running script: {scriptName}")

	try:
		encounters = _run(script, args, encounters)
	except Exception as e:
		log(logging.ERROR, str(e))
		try:
			telegram_send.send(messages=(f"Program crashed: {e}",))
		except telegram.error.NetworkError as ne:
			log(logging.ERROR, f"telegram_send: connection failed {ne}")
		raise
	finally:
		lib.dumpJson(encounterFile, jsn | {"pokemon": gameJson | {modName: modJson | {scriptName: encounters}}})
		log(logging.INFO, f"saved encounters: {encounters}")

		cv2.destroyAllWindows()

	return 0
