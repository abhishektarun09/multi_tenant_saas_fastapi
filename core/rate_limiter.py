import time
from collections import defaultdict
from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, max_calls: int, time_frame: int):
        self.max_calls = max_calls
        self.time_frame = time_frame
        self.calls: dict[str, list] = defaultdict(list)

    async def __call__(self, request: Request):
        client_ip = request.client.host
        now = time.time()
        self.calls[client_ip] = [
            t for t in self.calls[client_ip] if t > now - self.time_frame
        ]
        if len(self.calls[client_ip]) >= self.max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
        self.calls[client_ip].append(now)
