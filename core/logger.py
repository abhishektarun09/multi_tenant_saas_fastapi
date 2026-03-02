import logging
import sys
from logtail import LogtailHandler
from core.config import env

token = env.better_stack_token

logger = logging.getLogger()

formatter = logging.Formatter("%(asctime)s -  %(levelname)s - %(message)s")

stream_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler("app.log")
better_stack_handler = LogtailHandler(source_token=token)

stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.handlers = [stream_handler, file_handler, better_stack_handler]

logger.setLevel(logging.INFO)
