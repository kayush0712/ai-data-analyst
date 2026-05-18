import os

from dotenv import load_dotenv

load_dotenv()


def env(key, default=None):
    return os.getenv(key, default)


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

MONGO_URI = env("MONGO_URI")

CLOUDINARY_URL = env("CLOUDINARY_URL")
CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = env("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET")

SECRET_KEY = env("SECRET_KEY", "dev-secret-change-me")
TABLE_DISPLAY_LIMIT = int(env("TABLE_DISPLAY_LIMIT", "100"))

MPLCONFIGDIR = env("MPLCONFIGDIR", "/tmp/matplotlib")
