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
from lib.pokemon import Langs
from lib.pokemon import LOG_DELAY
from lib.pokemon import PokemonScript


Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-l", "--lang", action="store", choices=Langs, default=None, dest="tempLang", help="override lang for this run only (instead of using the one from config)")
Parser.add_argument("-s", "--shiny-dialog-delay", action="store_const", const=LOG_DELAY, default=logging.INFO, dest="shinyDelay", help="log dialog delay to file")
Parser.add_argument("-e", "--encounter-file", type=str, dest="encounterFile", default="encounters.json", help="file in which encounters are stored (defualt: %(default)s)")
Parser.add_argument("-n", "--send-nth-encounter", type=int, dest="sendNth", action="store", default=0, help="send every Nth encounter (must be 2 or higher; otherwise ignored)")
Parser.add_subparsers(dest="mod").add_parser("bdsp", parents=(ParserBDSP,))


def _run(scriptClass: Type[PokemonScript], args: dict[str, Any], encountersStart: int) -> int:
	modName = args.pop("mod")

	runnerPath = f"scripts.pokemon.{modName}._runner"
	try:
		return importlib.import_module(runnerPath).run(scriptClass, args, encountersStart)
	except ModuleNotFoundError:
		logging.critical(f"Failed to get runner module from {runnerPath}")
	except AttributeError:
		logging.critical(f"Failed to get runner function from {runnerPath}")

	return encountersStart


def run(args: dict[str, Any], modules: dict[str, Type[PokemonScript]]) -> int:
	modName: str = args["mod"]
	scriptName: str = args["script"]

	logging.debug(f"Mod:    {modName}")
	logging.debug(f"Script: {scriptName}")

	modulePath = f"scripts.pokemon.{modName}.{scriptName}"

	try:
		script = modules[modulePath]
	except KeyError:
		logging.critical(f"failed to get Script from {modulePath}")
		return 1

	encounterFile = args.pop("encounterFile")

	jsn = lib.loadJson(encounterFile)

	gameJson = jsn.get("pokemon", dict())
	modJson = gameJson.get(modName, dict())
	encounters = modJson.get(scriptName, 0)

	logging.info(f"Running script: {scriptName}")

	try:
		encounters = _run(script, args, encounters)
	except Exception as e:
		logging.error(e)
		try:
			telegram_send.send(messages=(f"Program crashed: {e}",))
		except telegram.error.NetworkError as ne:
			logging.error(f"telegram_send: connection failed {ne}")
		raise
	finally:
		lib.dumpJson(encounterFile, jsn | {"pokemon": gameJson | {modName: modJson | {scriptName: encounters}}})
		logging.info(f"saved encounters: {encounters}")

		cv2.destroyAllWindows()

	return 0
