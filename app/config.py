from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

# APP_ID = os.getenv("APP_ID")
# APP_SECRET = os.getenv("APP_SECRET")
# VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
# ENCRYPT_KEY = os.getenv("ENCRYPT_KEY")
# LARK_HOST = os.getenv("LARK_HOST")
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# OPENAI_API_KEY_SECOND = os.getenv('OPENAI_API_KEY_SECOND')
# print(f'VERIFICATION_TOKENVERIFICATION_TOKEN----{VERIFICATION_TOKEN}')
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

def get_env_value(key: str) -> str:
    return os.getenv(f"{key}_{ENVIRONMENT.upper()}")

APP_ID = get_env_value("APP_ID")
APP_SECRET = get_env_value("APP_SECRET")
VERIFICATION_TOKEN = get_env_value("VERIFICATION_TOKEN")
ENCRYPT_KEY = get_env_value("ENCRYPT_KEY")
LARK_HOST = os.getenv("LARK_HOST")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_KEY_SECOND = os.getenv('OPENAI_API_KEY_SECOND')