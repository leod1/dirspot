import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

def get_size(path):
    total = 0
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        for root, dirs, files in os.walk(path, topdown=True):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total += os.path.getsize(fp)
                except Exception:
                    pass
    except Exception:
        pass
    return total

async def scan_directory(path):
    loop = asyncio.get_event_loop()
    results = {}
    with ThreadPoolExecutor() as pool:
        if not os.path.isdir(path):
            return {}
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)
            size = await loop.run_in_executor(pool, get_size, full_path)
            results[full_path] = size
    return results