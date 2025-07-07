import asyncio
from scanner import scan_directory
from analyzer import sort_results, filter_results
from ui import display_tree

async def main():
    path = input("Entrez le chemin du dossier à analyser : ")
    print("Scan en cours...\n")
    results = await scan_directory(path)
    sorted_results = sort_results(results)
    display_tree(sorted_results)

if __name__ == "__main__":
    asyncio.run(main())