import logging
from datetime import datetime


_defaultFmt = logging.Formatter("[%(levelname)s] %(asctime)s %(message)s", "%Y/%m/%d-%H:%M:%S")

_streamHDLR = logging.StreamHandler()
_streamHDLR.setFormatter(_defaultFmt)

_debugFileHDLR = logging.FileHandler("logs/debug.log", "w+")
_debugFileHDLR.setFormatter(_defaultFmt)

_now = datetime.now()
_fileHDLR = logging.FileHandler(f"logs/switchcontroller-({_now.strftime('%Y-%m-%d')})-({_now.strftime('%H-%M-%S')}).log", "w+")
_fileHDLR.setFormatter(_defaultFmt)
del _now

_debugLogger = logging.getLogger("DEBUG")
_debugLogger.addHandler(_debugFileHDLR)
_debugLogger.setLevel(logging.DEBUG)

LOG_TRACE = logging.DEBUG - 1
logging.addLevelName(LOG_TRACE, "TRACE")

_infoLogger = logging.getLogger("INFO")
_infoLogger.addHandler(_streamHDLR)
_infoLogger.addHandler(_fileHDLR)
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

	_traceFileHDLR = logging.FileHandler("logs/_trace.log", "w+")
	_traceFileHDLR.setFormatter(_defaultFmt)

	_traceLogger = logging.getLogger("TRACE")
	_traceLogger.addHandler(_traceFileHDLR)
	_traceLogger.setLevel(LOG_TRACE)

	LOGGERS.append(_traceLogger)
