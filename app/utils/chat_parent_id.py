import json
import os
from utils.filesystem import index_cache_file_dir
PARENT_ID_MAPPING_FILE = index_cache_file_dir / "parent_id_mapping.json"
PARENT_CHILD_MAPPING_FILE = index_cache_file_dir / "parent_child_mapping.json"


def get_parent_id(parent_thread_id):
    if not os.path.exists(PARENT_ID_MAPPING_FILE):
        return None

    with open(PARENT_ID_MAPPING_FILE, 'r') as f:
        parent_id_mapping = json.load(f)

    return parent_id_mapping.get(str(parent_thread_id))


def write_parent_id(parent_thread_id, parent_id):
    parent_id_mapping = {}

    if os.path.exists(PARENT_ID_MAPPING_FILE):
        with open(PARENT_ID_MAPPING_FILE, 'r') as f:
            parent_id_mapping = json.load(f)

    parent_id_mapping[str(parent_thread_id)] = parent_id

    with open(PARENT_ID_MAPPING_FILE, 'w') as f:
        json.dump(parent_id_mapping, f)


def find_key_by_value(value: str, input_dict: dict) -> str:
    for key, val in input_dict.items():
        if val == value:
            return key
    return None


def write_parent_child_id(conversation_mapping):
    with open(PARENT_CHILD_MAPPING_FILE, 'w') as f:
        json.dump(conversation_mapping, f)


def get_info_from_file():
    with open(PARENT_CHILD_MAPPING_FILE, 'r') as f:
        return json.load(f)


def update_parent_child_id(conversation_id, parent_id):
    conversation_mapping = {}
    if os.path.exists(PARENT_CHILD_MAPPING_FILE):
        conversation_mapping = get_info_from_file()
    conversation_mapping[conversation_id] = parent_id
    write_parent_child_id(conversation_mapping)
