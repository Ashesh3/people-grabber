from json import load, dumps
from typing import Any, Dict


class ObserverDict(dict):
    def __setitem__(self, item, value):
        super(ObserverDict, self).__setitem__(item, value)
        with open("config.json", "w") as config_file:
            config_file.write(dumps(self, sort_keys=True, indent=4))


config: Dict[str, Any] = {}

with open("config.json", "r") as config_file:
    config = ObserverDict(load(config_file))
