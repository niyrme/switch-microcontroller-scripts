import argparse
import importlib
import logging
import os
import pathlib
from datetime import datetime
from typing import Type

from lib import RequirementsAction
from lib import Script
from lib.pokemon import LOG_DELAY


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
						modules[_sMod] = _script
						sp = _scriptParsers.add_parser(_scriptName, parents=[_script.parser()])
						# HACK couldn't find a way to jam it into `Script` and still work with subclasses
						sp.add_argument(
							"-r", "--requirements",
							action=RequirementsAction,
							help="print out the requirements for a script",
							requirements=_script.requirements,
						)

	args = vars(parser.parse_args())

	logging.root.setLevel(min(args[k] for k in ("debug", "shinyDelay")))

	logging.debug(f"setting log-level to {logging.getLevelName(logging.root.level)}")

	Nth = args["sendNth"]
	_Nth = str(Nth)

	if Nth >= 2:
		for (n, s) in (("11", "th"), ("12", "th"), ("13", "th"), ("1", "st"), ("2", "nd"), ("3", "rd")):
			if _Nth.endswith(n):
				m = s
				break
		else:
			m = "th"

		logging.info(f"sending screenshot of every {Nth}{m} encounter")

	gameName: str = args.pop("game")

	logging.debug(f"Game:   {gameName}")
	logging.debug(f"Mod:    {args['mod']}")
	logging.debug(f"Script: {args['script']}")

	runnerPath = f"scripts.{gameName}._runner"

	try:
		return importlib.import_module(runnerPath).run(args, modules)
	except ModuleNotFoundError:
		logging.critical(f"Failed to get runner module from {runnerPath}")
		return 1
	except AttributeError:
		logging.critical(f"Failed to get runner function from {runnerPath}")
		return 1


if __name__ == "__main__":
	# TODO get this outta here
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
