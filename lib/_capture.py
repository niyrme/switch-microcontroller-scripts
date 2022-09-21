import cv2
import numpy

from ._frame import Frame


class Capture:
	def __init__(self, *, width: int = 768, height: int = 480, fps: int = 30):
		self._vidWidth = width
		self._vidHeight = height

		vid = cv2.VideoCapture(0)
		vid.set(cv2.CAP_PROP_FPS, fps)
		vid.set(cv2.CAP_PROP_FRAME_WIDTH, width)
		vid.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

		self.vid: cv2.VideoCapture = vid

	@property
	def vidWidth(self) -> int:
		return self._vidWidth

	@property
	def vidHeight(self) -> int:
		return self._vidHeight

	def read(self) -> Frame:
		_, frame = self.vid.read()

		return Frame(frame)

	def getFrameRGB(self) -> numpy.ndarray:
		return cv2.cvtColor(self.read().ndarray, cv2.COLOR_BGR2RGB)

	def __del__(self):
		if hasattr(self, "vid"):
			if self.vid.isOpened():
				self.vid.release()
