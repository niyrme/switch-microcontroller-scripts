from abc import abstractmethod

from lib import Frame


class Notify:
	@abstractmethod
	def send(self, **kwargs):
		raise NotImplementedError

	@abstractmethod
	def sendMessage(self, msg: str, **kwargs):
		raise NotImplementedError

	@abstractmethod
	def sendImage(self, frame: Frame, **kwargs):
		raise NotImplementedError
