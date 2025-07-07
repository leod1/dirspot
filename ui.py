from rich.tree import Tree
from rich import print
from rich.console import Console
import os

console = Console()

def human_readable_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def display_tree(results):
    tree = Tree("[bold green]Analyse de l'espace disque")
    for path, size in results.items():
        tree.add(f"[yellow]{os.path.basename(path)}[/yellow] - [red]{human_readable_size(size)}[/red]")
    console.print(tree)