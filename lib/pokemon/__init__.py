import logging

LOG_DELAY = logging.DEBUG - 1

logging._levelToName.update({LOG_DELAY: "DELAY"})
logging._nameToLevel.update({"DELAY": LOG_DELAY})
