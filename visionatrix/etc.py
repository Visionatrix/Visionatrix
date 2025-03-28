import logging
import os
import string
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
]

TEXT_EXTENSIONS = [
    ".txt",
]

MODEL3D_EXTENSION = [
    ".glb",
]


def get_log_level(log_level_str):
    """Convert log level string to logging module log level."""
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return log_levels.get(log_level_str.upper(), logging.INFO)


def get_higher_log_level(current_level):
    level_mapping = {
        logging.DEBUG: logging.INFO,
        logging.INFO: logging.WARNING,
        logging.WARNING: logging.ERROR,
        logging.ERROR: logging.ERROR,
        logging.CRITICAL: logging.CRITICAL,
    }
    return level_mapping.get(current_level, logging.WARNING)


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
