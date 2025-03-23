import asyncio
import threading

EXIT_EVENT = threading.Event()
EXIT_EVENT_ASYNC = asyncio.Event()
