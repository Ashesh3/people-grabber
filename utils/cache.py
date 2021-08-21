from sqlitedict import SqliteDict
import zlib, pickle, sqlite3
from utils.config import config


cache = SqliteDict(
    config["CACHE_PATH"],
    encode=lambda obj: sqlite3.Binary(zlib.compress(pickle.dumps(obj, pickle.HIGHEST_PROTOCOL), 9)),
    decode=lambda obj: pickle.loads(zlib.decompress(bytes(obj))),
    autocommit=True,
)
