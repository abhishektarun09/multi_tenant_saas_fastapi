import time
from fastapi import Request

from core.logger import logger


async def log_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    end_time = time.time()
    duration = end_time - start_time

    log_dict = {
        "url": request.url.path,
        "method": request.method,
        "processing_time": duration,
        "status_code": response.status_code,
        "client_ip": request.client.host,
        "user_agent": request.headers.get("user-agent"),
        "referer": request.headers.get("referer"),
        "request_id": request.headers.get("x-request-id"),
    }
    logger.info(log_dict, extra=log_dict)

    return response
