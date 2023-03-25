import argparse
import logging
from typing import Any

import cv2
import yaml

from lib import Capture
from lib import log


Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("--fps", type=int, default=30, dest="fps", help="fps of the capture")
Parser.add_argument("--width", type=int, default=768, dest="width", help="width of the capture")
Parser.add_argument("--height", type=int, default=480, dest="height", help="height of the capture")


def run(args: dict[str, Any]) -> int:
	with open(args.pop("configFile"), "r") as fp:
		cfg: dict[str, Any] = yaml.safe_load(fp)

	log(logging.INFO, "setting up cv2. This may take a while...")
	cap = Capture(
		camID=cfg.pop("cameraID", 0),
		width=args.pop("width"),
		height=args.pop("height"),
		fps=args.pop("fps"),
	)

	log(logging.INFO, "Press Ctrl+C to stop rendering")
	try:
		while True:
			cv2.imshow("Switch Render", cap._read())
			if cv2.waitKey(1) & 0xFF == ord("q"):
				break
	except KeyboardInterrupt:
		pass

	return 0
