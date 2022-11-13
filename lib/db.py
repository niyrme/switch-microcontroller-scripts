import json
from typing import Any
from typing import Final
from typing import final

import mergedeep


# too lazy to learn SQL or other DBs
@final
class DB:
	def __init__(self, fileName: str) -> None:
		self._fileName: Final[str] = fileName

	def get(self, key: str) -> Any:
		with open(self._fileName, "r") as fp:
			jsn: dict[str, Any] = json.load(fp)

		def _getR(keys: list[str]) -> Any:
			nonlocal jsn

			jsn = jsn[keys.pop(0)]

			if len(keys) == 0:
				return jsn
			else:
				return _getR(keys)

		return _getR(key.split("."))

	def set(self, key: str, value: Any) -> None:
		def _setR(keys: list[str]) -> dict[str, Any]:
			nonlocal value
			k = keys.pop(0)

			if len(keys) == 0:
				return {k: value}
			else:
				return {k: _setR(keys)}

		with open(self._fileName, "r") as fp:
			oldData = json.load(fp)

		data = mergedeep.merge(oldData, _setR(key.split(".")), strategy=mergedeep.Strategy.TYPESAFE_REPLACE)

		with open(self._fileName, "w") as fp:
			json.dump(data, fp, sort_keys=True, indent="\t")

	def getOrInsert(self, key: str, value: Any) -> Any:
		try:
			return self.get(key)
		except KeyError:
			self.set(key, value)
			return value
