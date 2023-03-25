import logging

from .discord import Discord as Discord  # noqa: 401
from .notify import Notify as Notify  # noqa: 401
from .telegram import Telegram as Telegram  # noqa: 401
from lib import Frame
from lib import log


class Notifier:
	def __init__(self) -> None:
		self.notifiers: list[Notify] = []

	def add(self, notifier: Notify):
		self.notifiers.append(notifier)

	def sendMessage(self, msg: str, **kwargs):
		for n in self.notifiers:
			n.sendMessage(msg, **kwargs)

	def sendImage(self, frame: Frame, **kwargs):
		for n in self.notifiers:
			n.sendImage(frame, **kwargs)

	def sendTo(self, notifierName: str, **kwargs):
		log(logging.DEBUG, f"{notifierName=}")
		for notifier in self.notifiers:
			log(logging.DEBUG, f"{notifier.__class__.__name__=}")
			if notifier.__class__.__name__ == notifierName:
				log(logging.DEBUG, f"[{notifier.__class__.__name__}] send: {kwargs=}")
				notifier.send(**kwargs)
