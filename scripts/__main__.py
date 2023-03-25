import argparse
import importlib
import logging
import pathlib
from typing import Any
from typing import Callable

from lib import log


SELF = pathlib.Path(__file__)


def main() -> int:
	parser = argparse.ArgumentParser(prog="switchScripts")
	parser.add_argument("-c", "--config-file", dest="configFile", default="config.yaml", help="configuration file (defualt: %(default)s)")
	parser.add_argument("-t", "--trace", action="store_true", default="trace")

	gamesParsers = None

	for _game in filter(
		lambda p: p.is_dir() and not p.name.startswith("_"),
		SELF.parent.iterdir(),
	):
		if _game.name == "other": continue
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
			raise

	others = set()
	for other in (SELF.parent / "other").iterdir():
		name = other.name
		if not other.is_file() or name.startswith("_") or not name.endswith(".py"):
			continue

		name = name[:-3]
		pth = f"scripts.other.{name}"

		try:
			_other = importlib.import_module(pth)
		except ModuleNotFoundError:
			log(logging.WARNING, f"failed to import {pth}")
			raise

		gamesParsers = gamesParsers or parser.add_subparsers(dest="other")
		try:
			gamesParsers.add_parser(name, parents=(_other.Parser,))
			others.add(name)
		except AttributeError:
			log(logging.WARNING, f"failed to get Parser from {pth}")
			raise

	args = vars(parser.parse_args())

	if args.pop("trace") is True:
		from lib._logging import addTrace
		addTrace()

	if (game := args.pop("game")) in others:
		runnerPath = f"scripts.other.{game}"
	else:
		runnerPath = f"scripts.{game}._runner"

	try:
		runFn: Callable[[dict[str, Any]], int] = importlib.import_module(runnerPath).run
	except ModuleNotFoundError:
		log(logging.CRITICAL, f"Failed to get runner module from {runnerPath}")
		raise
	except AttributeError:
		log(logging.CRITICAL, f"Failed to get runner function from {runnerPath}")
		raise

	return runFn(args)


if __name__ == "__main__":
	raise SystemExit(main())
