import os
from dotenv import load_dotenv

# load .env file
load_dotenv()

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Database settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "testdb")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_PORT = int(os.getenv("DB_PORT", 3306))

NITB_ID = os.getenv("NITB_ID")
NITB_PASS = os.getenv("NITB_PASS")
NITB_BASE = os.getenv("NITB_BASE", "https://admin-icta.nitb.gov.pk")

ARMS_DB_HOST = os.getenv("ARMS_DB_HOST", "localhost")
ARMS_DB_NAME = os.getenv("ARMS_DB_NAME", "testdb")
ARMS_DB_USER = os.getenv("ARMS_DB_USER", "root")
ARMS_DB_PASS = os.getenv("ARMS_DB_PASS", "")
ARMS_DB_PORT = int(os.getenv("ARMS_DB_PORT", 3306))