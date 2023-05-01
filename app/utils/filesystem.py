import os
from pathlib import Path
import hashlib

home_dir = os.path.expanduser("~")
index_cache_web_dir = Path('/tmp/myGPTReader/cache_web/')
index_cache_file_dir = Path(home_dir, "myGPTReader", "file")
if not index_cache_file_dir.is_dir():
    index_cache_file_dir.mkdir(parents=True, exist_ok=True)


def get_file_extension(filename):
    _, file_extension = os.path.splitext(filename)
    return file_extension[1:]  # 使用字符串切片去掉点


def md5_file_con(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_unique_md5(str):
    hashed_str = hashlib.md5(str.encode('utf-8')).hexdigest()
    return hashed_str


def get_json_path(md5_source):
    index_file_name = get_unique_md5(md5_source)
    index = index_cache_web_dir / index_file_name
    if not index.is_dir():
        index.mkdir(parents=True, exist_ok=True)
    json_path = index / "result.json"
    return json_path
