def sort_results(results):
    return dict(sorted(results.items(), key=lambda item: item[1], reverse=True))

def filter_results(results, min_size=0):
    return {path: size for path, size in results.items() if size >= min_size}