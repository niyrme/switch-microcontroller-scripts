import cv2
import numpy
import serial

from lib import Config
from lib import ReturnCode
from lib.pokemon.bdsp import Gen4Script


class Script(Gen4Script):
	def __init__(self, ser: serial.Serial, vid: cv2.VideoCapture, config: Config, **kwargs) -> None:
		super().__init__(ser, vid, config, **kwargs, windowName="Pokermans: Arceus")
		raise NotImplementedError("Arceus script is currently only a placeholder for the real thing later on")

	def main(self, e: int) -> tuple[int, ReturnCode, numpy.ndarray]:
		raise NotImplementedError("Arceus script is currently only a placeholder for the real thing later on")
