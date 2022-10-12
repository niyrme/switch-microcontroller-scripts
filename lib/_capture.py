import logging
import threading
from threading import Thread
from typing import final

import cv2
import numpy

from ._frame import Frame
from ._logging import log


_THREAD_VIDCAP = "Thread-VideoCapture_update"
_THREAD_VIDWRITE = "Thread-VideoWriter"


@final
class Capture:
	def __init__(self, *, camID: int = 0, width: int = 768, height: int = 480, fps: int = 30) -> None:
		"""
		@param render whether to render the video capture
		@param windowName name of the window which renders the capture
		@param camID camera ID to read
		@param width width of capture
		@param height height of capture
		@param fps fps of capture
		"""

		self._width = width
		self._height = height
		self._fps = fps

		self._isCapturing = False

		self.vid = self._setupCapture(camID)

		_, f = self.vid.read()
		self._frame: numpy.ndarray = f

		self._writeThread: Thread

		self._frameLock = threading.Lock()
		self._doRead = True
		self._readThread = Thread(target=self._update, name=_THREAD_VIDCAP, daemon=True)
		self._readThread.start()

	def __del__(self):
		self._doRead = False

		if self.vid.isOpened():
			self.vid.release()

		if self._isCapturing is True:
			log(logging.DEBUG, "Stopping running capture")
			self.stopCapture()

		log(logging.DEBUG, "Waiting for VideoCapture thread to stop...")
		self._readThread.join()

	def _setupCapture(self, id: int) -> cv2.VideoCapture:
		vid = cv2.VideoCapture(id)
		vid.set(cv2.CAP_PROP_FPS, self._fps)
		vid.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
		vid.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)

		return vid

	def _update(self) -> None:
		log(logging.DEBUG, f"{_THREAD_VIDCAP} is running")

		ok, frame = self.vid.read()

		try:
			while self._doRead is True:
				ok, frame = self.vid.read()
				with self._frameLock:
					if ok is True:
						self._frame = frame
					else:
						log(logging.WARNING, "Failed to read from VideoCapture")
		except Exception as e:
			log(logging.ERROR, f"{_THREAD_VIDCAP} has crashed: {e}")
		finally:
			log(logging.DEBUG, f"{_THREAD_VIDCAP} is stopping")

	@property
	def width(self) -> int:
		return self._width

	@property
	def height(self) -> int:
		return self._height

	@property
	def fps(self) -> int:
		return self._fps

	@property
	def isCapturing(self) -> bool:
		return self._isCapturing

	def _read(self) -> numpy.ndarray:
		with self._frameLock:
			frame = self._frame.copy()
		return frame

	def read(self) -> Frame:
		return Frame(self._read())

	def startCapture(self, path: str) -> None:
		# FIXME
		return
		if self._isCapturing:
			log(logging.WARNING, "A capture is already running")
			return

		def _runCap() -> None:
			nonlocal self
			log(logging.DEBUG, f"{_THREAD_VIDWRITE} is running")
			height = int(self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
			width = int(self.vid.get(cv2.CAP_PROP_FRAME_WIDTH))

			writer = cv2.VideoWriter(f"{path}.avi", cv2.VideoWriter_fourcc(*"MJPG"), 30.0, (width, height), True)

			assert writer.isOpened()

			try:
				while self._isCapturing is True:
					writer.write(self._read())
			finally:
				log(logging.DEBUG, f"{_THREAD_VIDWRITE} is stopping")
				writer.release()

		self._isCapturing = True
		self._writeThread = Thread(target=_runCap, name=_THREAD_VIDWRITE)
		self._writeThread.start()

	def stopCapture(self) -> None:
		# FIXME
		return
		if self._isCapturing is True:
			self._isCapturing = False
			self._writeThread.join()
