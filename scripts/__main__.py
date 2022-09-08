import argparse
import importlib
import logging
import os
import pathlib

from lib import log


def main() -> int:
	parser = argparse.ArgumentParser(prog="switchScripts")
	parser.add_argument("-c", "--config-file", type=str, dest="configFile", default="config.yaml", help="configuration file (defualt: %(default)s)")
	parser.add_argument("-t", "--trace", action="store_true", default="trace")

	path = pathlib.Path(__file__)

	gamesParsers = None

	for _game in filter(
		lambda p: p.is_dir() and not p.name.startswith("_"),
		path.parent.iterdir(),
	):
		_gamePath = f"scripts.{_game.name}._runner"

		try:
			game = importlib.import_module(_gamePath)
		except ModuleNotFoundError:
			log(logging.WARNING, f"failed to import {_gamePath}")
			continue

		gamesParsers = gamesParsers or parser.add_subparsers(dest="game")
		try:
			gamesParsers.add_parser(_game.name, parents=(game.Parser,))
		except AttributeError:
			log(logging.WARNING, f"failed to get Parser from {_gamePath}")
			continue

	args = vars(parser.parse_args())

	Nth = args["sendNth"]
	_Nth = str(Nth)

	if args.pop("trace") is True:
		from lib._logging import addTrace
		addTrace()

	if Nth >= 2:
		for (n, s) in ((("11", "12", "13"), "th"), ("1", "st"), ("2", "nd"), ("3", "rd")):
			if _Nth.endswith(n):
				m = s
				break
		else:
			m = "th"

		log(logging.INFO, f"sending screenshot of every {Nth}{m} encounter")

	gameName: str = args.pop("game")

	runnerPath = f"scripts.{gameName}._runner"

	try:
		return importlib.import_module(runnerPath).run(args)
	except ModuleNotFoundError:
		log(logging.CRITICAL, f"Failed to get runner module from {runnerPath}")
		return 1
	except AttributeError:
		log(logging.CRITICAL, f"Failed to get runner function from {runnerPath}")
		return 1


if __name__ == "__main__":
	os.makedirs("logs", exist_ok=True)

	raise SystemExit(main())
