import os
import tempfile

import cv2
import discordwebhook

from .notify import Notify
from lib import Frame


class Discord(Notify):
	def __init__(self, url: str) -> None:
		super().__init__()
		self.discord = discordwebhook.Discord(url=url)

	def send(self, **kwargs):
		self.discord.post(**kwargs)

	def sendMessage(self, msg: str, **kwargs):
		self.send(content=msg, **kwargs)

	def sendImage(self, frame: Frame, **kwargs):
		with tempfile.TemporaryDirectory() as tempDirName:
			path = os.path.join(tempDirName, "screenshot.png")
			cv2.imwrite(path, frame.ndarray)
			with open(path, "rb") as img:
				self.send(file={"encounter": img}, **kwargs)
