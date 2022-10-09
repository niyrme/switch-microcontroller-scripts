import argparse
import importlib
import logging
import pathlib

from lib import log


def main() -> int:
	parser = argparse.ArgumentParser(prog="switchScripts")
	parser.add_argument("-c", "--config-file", type=str, dest="configFile", default="config.yaml", help="configuration file (defualt: %(default)s)")
	parser.add_argument("-t", "--trace", action="store_true", default="trace")

	gamesParsers = None

	for _game in filter(
		lambda p: p.is_dir() and not p.name.startswith("_"),
		pathlib.Path(__file__).parent.iterdir(),
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

	log(logging.DEBUG, f"{args=}")

	if args.pop("trace") is True:
		from lib._logging import addTrace
		addTrace()

	runnerPath = f"scripts.{args.pop('game')}._runner"

	try:
		return importlib.import_module(runnerPath).run(args)
	except ModuleNotFoundError:
		log(logging.CRITICAL, f"Failed to get runner module from {runnerPath}")
		return 1
	except AttributeError:
		log(logging.CRITICAL, f"Failed to get runner function from {runnerPath}")
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
