import logging
from typing import Final


_streamFmt = logging.Formatter("[%(levelname)s] %(asctime)s %(message)s", "%H:%M:%S")
_fileFmt = logging.Formatter(
	'{ "level": "%(levelname)s", "timestamp": "%(asctime)s", "msg": "%(message)s" }',
	datefmt="%Y/%m/%d-%H:%M:%S",
)

_streamHDLR = logging.StreamHandler()
_streamHDLR.setFormatter(_streamFmt)

_debugFileHDLR = logging.FileHandler("debug.log", "w+")
_debugFileHDLR.setFormatter(_fileFmt)

_infoFileHDLR = logging.FileHandler("switchController.log", "a+")
_infoFileHDLR.setFormatter(_fileFmt)

_debugLogger = logging.getLogger("DEBUG")
_debugLogger.addHandler(_debugFileHDLR)
_debugLogger.setLevel(logging.DEBUG)

LOG_TRACE: Final[int] = logging.DEBUG - 1
logging.addLevelName(LOG_TRACE, "TRACE")

_infoLogger = logging.getLogger("INFO")
_infoLogger.addHandler(_streamHDLR)
_infoLogger.addHandler(_infoFileHDLR)
_infoLogger.setLevel(logging.INFO)


global LOGGERS
LOGGERS = [
	_debugLogger,
	_infoLogger,
]


def log(level: int, msg: str) -> None:
	for lgr in LOGGERS:
		lgr.log(level, msg)


def addTrace() -> None:
	global LOGGERS

	_traceFileHDLR = logging.FileHandler("trace.log", "w+")
	_traceFileHDLR.setFormatter(_fileFmt)

	_traceLogger = logging.getLogger("TRACE")
	_traceLogger.addHandler(_traceFileHDLR)
	_traceLogger.setLevel(LOG_TRACE)

	LOGGERS.append(_traceLogger)
