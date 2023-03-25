import logging
import os
import tempfile

import cv2
import telegram
import telegram_send

from .notify import Notify
from lib import Frame
from lib import log


class Telegram(Notify):
	def __init__(self) -> None:
		super().__init__()

	def send(self, **kwargs):
		try:
			telegram_send.send(**kwargs)
		except telegram.error.NetworkError as e:
			log(logging.WARNING, f"telegram_send: connection failed: {e}")

	def sendMessage(self, msg: str, **kwargs):
		self.send(messages=(msg,), **kwargs)

	def sendImage(self, frame: Frame, **kwargs):
		with tempfile.TemporaryDirectory() as tempDirName:
			path = os.path.join(tempDirName, "screenshot.png")
			cv2.imwrite(path, frame.ndarray)
			with open(path, "rb") as img:
				self.send(images=(img,), **kwargs)
