import logging

LOG_DELAY = logging.INFO - 1

logging._levelToName.update({LOG_DELAY: "DELAY"})
logging._nameToLevel.update({"DELAY": LOG_DELAY})
