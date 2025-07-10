import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

def get_file_size(path):
    try:
        return os.path.getsize(path)
    except (OSError, FileNotFoundError):
        return 0

async def list_dir(loop, executor, path):
    try:
        return await loop.run_in_executor(executor, os.listdir, path)
    except (PermissionError, FileNotFoundError):
        return []

async def scan_directory_recursive(path, cache, loop=None, executor=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=32)

    if not os.path.isdir(path):
        return {}, 0, 0

    entries = await list_dir(loop, executor, path)

    results = {}
    total_size = 0
    file_count = 0
    dir_count = 1

    file_tasks = []
    subdir_paths = []

    for entry in entries:
        full_path = os.path.join(path, entry)
        if os.path.isfile(full_path):
            results[full_path] = None
            file_tasks.append(loop.run_in_executor(executor, get_file_size, full_path))
        elif os.path.isdir(full_path):
            subdir_paths.append(full_path)

    # Lancer en parallèle la récupération des tailles
    file_sizes = await asyncio.gather(*file_tasks)
    for i, file_path in enumerate([p for p in results if results[p] is None]):
        size = file_sizes[i]
        results[file_path] = size
        total_size += size
        file_count += 1

    # Lancer les scans de sous-dossiers en parallèle
    subdir_tasks = [
        scan_directory_recursive(subdir, cache, loop, executor)
        for subdir in subdir_paths
    ]
    subdir_results = await asyncio.gather(*subdir_tasks)

    for subdir, (sub_res, sub_files, sub_dirs) in zip(subdir_paths, subdir_results):
        cache[subdir] = sub_res
        sub_total = sum(sub_res.values())
        results[subdir] = sub_total
        total_size += sub_total
        file_count += sub_files
        dir_count += sub_dirs

    cache[path] = results
    return results, file_count, dir_count
