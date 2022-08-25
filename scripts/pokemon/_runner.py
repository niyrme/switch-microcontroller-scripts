import importlib
import logging
from typing import Any
from typing import Type

import cv2
import telegram
import telegram_send

import lib
from lib.pokemon.bdsp import BDSPScript


PokemonScript = Type[BDSPScript]


def _run(scriptClass: PokemonScript, args: dict[str, Any], encountersStart: int) -> int:
	modName = args.pop("mod")

	runnerPath = f"scripts.pokemon.{modName}._runner"
	try:
		return importlib.import_module(runnerPath).run(scriptClass, args, encountersStart)
	except ModuleNotFoundError:
		logging.critical(f"Failed to get runner module from {runnerPath}")
	except AttributeError:
		logging.critical(f"Failed to get runner function from {runnerPath}")

	return encountersStart


def run(args: dict[str, Any], modules: dict[str, PokemonScript]) -> int:
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
		if script.storeEncounters is True:
			lib.dumpJson(encounterFile, jsn | {"pokemon": gameJson | {modName: modJson | {scriptName: encounters}}})
			logging.info(f"saved encounters: {encounters}")

		cv2.destroyAllWindows()

	return 0
