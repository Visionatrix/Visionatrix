import logging
import os
import string
import sys
from contextlib import contextmanager

IMAGE_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".svg",
    ".ico",
    ".heif",
    ".heic",
    ".hif",
    ".raw",
    ".psd",
    ".eps",
    ".avif",
    ".jp2",
    ".xcf",
]

IMAGE_ANIMATED_EXTENSIONS = [
    ".gif",
    ".webp",
]

VIDEO_EXTENSIONS = [
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",
    ".flv",
    ".wmv",
    ".webm",
    ".m4v",
    ".3gp",
    ".3g2",
    ".mpg",
    ".mpeg",
    ".vob",
    ".rm",
    ".rmvb",
    ".ts",
    ".m2ts",
    ".mxf",
    ".f4v",
    ".divx",
    ".xvid",
    ".ogv",
    ".mpe",
    ".asf",
    ".swf",
]

AUDIO_EXTENSIONS = [
    ".mp3",
    ".flac",
    ".wav",
]

TEXT_EXTENSIONS = [
    ".txt",
]

MODEL3D_EXTENSION = [
    ".glb",
    ".gltf",
    ".fbx",
]

DEFAULT_LOG_FORMAT = "%(asctime)s: [%(funcName)s]:%(levelname)s: %(message)s"
DEFAULT_DATE_FORMAT = "%H:%M:%S"


def get_higher_log_level(current_level):
    level_mapping = {
        logging.DEBUG: logging.INFO,
        logging.INFO: logging.WARNING,
        logging.WARNING: logging.ERROR,
        logging.ERROR: logging.ERROR,
        logging.CRITICAL: logging.CRITICAL,
    }
    return level_mapping.get(current_level, logging.WARNING)


def setup_logging(
    log_level_name: str = "INFO", log_format: str = DEFAULT_LOG_FORMAT, date_format: str = DEFAULT_DATE_FORMAT
):
    requested_level_name = log_level_name.upper()
    log_level = logging.getLevelName(log_level_name.upper())
    if not isinstance(log_level, int):
        print(f"Warning: Invalid log level name '{log_level_name}'. Defaulting to INFO.", file=sys.stderr)
        log_level = logging.INFO
        resolved_log_level_name = logging.getLevelName(log_level)
    else:
        resolved_log_level_name = requested_level_name

    # Set Environment Variable (Important: BEFORE configuring loggers that might read it)
    # This makes the resolved level available to child processes or other parts
    # of the current process that might check the environment later.
    os.environ["LOG_LEVEL"] = resolved_log_level_name
    logger = logging.getLogger("visionatrix")
    logger.setLevel(log_level)  # Set level for the application logger FIRST

    # Check if a handler of the correct type and target (stdout/stderr) already exists
    # to prevent duplicates, especially relevant if called multiple times or in complex setups.
    handler_exists = False
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and h.stream in (sys.stdout, sys.stderr):
            handler_exists = True
            h.setLevel(log_level)
            formatter = logging.Formatter(log_format, datefmt=date_format)
            h.setFormatter(formatter)
            break  # Assume one console handler is enough

    if not handler_exists:
        handler = logging.StreamHandler(sys.stdout)  # Use stdout for all log levels
        handler.setLevel(log_level)  # Crucial: Handler must also have the level set
        formatter = logging.Formatter(log_format, datefmt=date_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Prevent messages from propagating to the root logger if we have our own handler.
    # This stops potential double logging if the root logger is configured separately  (e.g., by default or by Uvicorn).
    logger.propagate = False

    # Make noisy libraries less verbose unless we are in DEBUG mode
    dependency_level = log_level if log_level == logging.DEBUG else get_higher_log_level(log_level)
    logging.getLogger("httpx").setLevel(dependency_level)
    logging.getLogger("alembic").setLevel(dependency_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if log_level > logging.DEBUG else logging.DEBUG)


def is_english(input_string: str) -> bool:
    english_letters = set(string.ascii_letters)
    words = input_string.split()
    if not words:
        return True

    english_word_count = 0
    for word in words:
        cleaned_word = "".join(char for char in word if char.isalpha())
        if all(char in english_letters for char in cleaned_word) and cleaned_word:
            english_word_count += 1

    return english_word_count / len(words) > 0.90  # Check if more than 90% of the words are in English


@contextmanager
def temporary_env_var(key: str, new_value):
    old_value = os.environ.get(key)
    if new_value is not None:
        os.environ[key] = new_value
    elif key in os.environ:
        del os.environ[key]
    try:
        yield
    finally:
        if old_value is not None:
            os.environ[key] = old_value
        elif key in os.environ:
            del os.environ[key]
