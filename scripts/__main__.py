import argparse
import importlib
import logging
import os
import pathlib
from datetime import datetime
from typing import Type

from lib import Script


def main() -> int:
	parser = argparse.ArgumentParser(prog="switchScripts")
	parser.add_argument("-d", "--debug", action="store_const", const=logging.DEBUG, default=logging.INFO, dest="debug", help="output debugging info")
	parser.add_argument("-c", "--config-file", type=str, dest="configFile", default="config.yaml", help="configuration file (defualt: %(default)s)")

	path = pathlib.Path(__file__)

	gameScripts: dict[str, Type[Script]] = {}
	gamesParsers = None

	for _game in filter(
		lambda p: p.is_dir(),
		path.parent.iterdir(),
	):
		_gameName = _game.name
		_gamePath = f"scripts.{_gameName}._runner"

		try:
			game = importlib.import_module(_gamePath)
		except ModuleNotFoundError:
			logging.warning(f"Failed to import {_gamePath}")
			continue

		gamesParsers = gamesParsers or parser.add_subparsers(dest="game")
		try:
			gamesParsers.add_parser(_gameName, parents=(game.Parser,))
		except AttributeError:
			logging.warning(f"Failed to get Parser from {_gamePath}")
			continue

		try:
			gameScripts[_gameName] = game.Script
		except AttributeError:
			logging.warning(f"Failed to get Script from {_gamePath}")
			continue

	args = vars(parser.parse_args())

	import pprint
	pprint.pp(args)
	return 0

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
		return importlib.import_module(runnerPath).run(args, gameScripts)
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
