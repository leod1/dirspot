from concurrent.futures import ThreadPoolExecutor
import sys
import os
import asyncio
import squarify
import matplotlib
import shutil
from time import perf_counter

matplotlib.use('QtAgg')
matplotlib.rcParams['backend'] = 'QtAgg'

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QTreeWidget, QTreeWidgetItem, QLabel, QMessageBox,
    QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal

from scanner import scan_directory_recursive
from analyzer import sort_results
from ui import human_readable_size


# --- Canvas Treemap ---
class TreemapCanvas(QWidget):
    def __init__(self, sizes, labels):
        super().__init__()
        self.canvas = FigureCanvas(Figure(figsize=(6, 4)))
        self.canvas.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 8px;")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.axes = self.canvas.figure.add_subplot(111)
        self.canvas.figure.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
        self.plot_treemap(sizes, labels)

    def plot_treemap(self, sizes, labels):
        self.axes.clear()
        squarify.plot(sizes=sizes, label=labels, ax=self.axes, pad=True, text_kwargs={'fontsize': 8})
        self.axes.axis('off')
        self.canvas.draw()


# --- Thread worker ---
class Worker(QThread):
    result_ready = Signal(str, dict, float, dict)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        start = perf_counter()
        full_cache = {}

        with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
            results, file_count, dir_count = loop.run_until_complete(
                scan_directory_recursive(self.path, full_cache, loop=loop, executor=executor)
            )

        self.sanityze_cache(full_cache)
        duration = perf_counter() - start
        sorted_root = sort_results(results)

        flat_cache = {}
        for dir_path, content in full_cache.items():
            if isinstance(content, dict):
                flat_cache[dir_path] = content

        self.result_ready.emit(self.path, sorted_root, duration, flat_cache)

    @staticmethod
    def sanityze_cache(cache: dict) -> None:
        def convert_path(path: str) -> str:
            return path.replace('\\', '/')

        keys_to_update = list(cache.keys())
        for old_parent in keys_to_update:
            new_parent = convert_path(old_parent)
            files = cache.pop(old_parent)

            if isinstance(files, dict):
                subkeys_to_update = list(files.keys())
                for old_child in subkeys_to_update:
                    new_child = convert_path(old_child)
                    if new_child != old_child:
                        files[new_child] = files.pop(old_child)

            cache[new_parent] = files


# --- Application principale ---
class DiskAnalyzerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIRSPOT - Analyseur de disque")
        self.setMinimumSize(700, 500)

        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 6px;
                background-color: #2980b9;
                color: white;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #1c6690;
            }
            QLabel {
                margin: 4px;
            }
            QTreeWidget {
                background-color: #f9f9f9;
                border: 1px solid #ccc;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                padding: 4px;
                font-weight: bold;
                border: 1px solid #bdc3c7;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.label = QLabel("Sélectionnez un dossier à analyser.")
        main_layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        self.breadcrumb_layout = QHBoxLayout()
        main_layout.addLayout(self.breadcrumb_layout)

        self.button = QPushButton("Choisir un dossier")
        self.button.clicked.connect(self.choose_folder)
        main_layout.addWidget(self.button)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Type", "Nom", "Taille", "Actions"])
        self.tree.setColumnWidth(0, 70)
        self.tree.itemClicked.connect(self.on_item_clicked)
        main_layout.addWidget(self.tree)

        self.canvas = None
        self.scan_cache = {}
        self.current_folder = None

        # --- Barre disque compacte ---
        self.disk_bar = QProgressBar()
        self.disk_bar.setTextVisible(False)
        self.disk_bar.setFixedSize(200, 10)
        self.disk_bar.setMaximum(100)
        self.disk_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #aaa;
                border-radius: 3px;
                background-color: #eee;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
            }
        """)

        self.disk_label = QLabel("")
        disk_layout = QHBoxLayout()
        disk_layout.addWidget(self.disk_bar)
        disk_layout.addWidget(self.disk_label)
        disk_layout.addStretch()

        main_layout.addLayout(disk_layout)

        self.setLayout(main_layout)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if folder:
            self.start_scan(folder)

    def start_scan(self, folder):
        folder = folder.replace('\\', '/')
        self.label.setText(f"📁 Analyse en cours : {folder}")
        self.progress_bar.show()
        self.tree.clear()
        self.clear_breadcrumb()
        if self.canvas:
            self.layout().removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas = None

        self.current_folder = folder
        self.build_breadcrumb(folder)

        if folder in self.scan_cache:
            self.progress_bar.hide()
            results = self.scan_cache[folder]
            self.update_tree(results, duration=0, count=len(results))
            self.show_mosaic()
            self.update_disk_usage_bar(folder)
        else:
            self.worker = Worker(folder)
            self.worker.result_ready.connect(self.handle_scan_results)
            self.worker.start()

    def handle_scan_results(self, folder, results, duration, flat_cache):
        self.progress_bar.hide()
        self.scan_cache.update(flat_cache)
        self.scan_cache[folder] = results
        self.current_folder = folder
        self.build_breadcrumb(folder)
        self.update_tree(results, duration, len(flat_cache))
        self.show_mosaic()
        self.update_disk_usage_bar(folder)

    def update_disk_usage_bar(self, path):
        try:
            total, used, free = shutil.disk_usage(path)
            percent = used / total * 100
            self.disk_bar.setValue(int(percent))
            self.disk_label.setText(f"{human_readable_size(used)} of {human_readable_size(total)} used")
        except Exception:
            self.disk_label.setText("Disk info unavailable")
            self.disk_bar.setValue(0)

    def update_tree(self, results, duration=0, count=0):
        self.last_results = results
        sorted_items = sorted(results.items(), key=lambda item: item[1], reverse=True)

        self.tree.clear()
        for path, size in sorted_items:
            name = os.path.basename(path) or path
            icon = "📁" if os.path.isdir(path) else "📃"
            item = QTreeWidgetItem([icon, name, human_readable_size(size), ""])
            item.setData(1, Qt.UserRole, path)
            self.tree.addTopLevelItem(item)

            delete_button = QPushButton("🗑 Supprimer")
            delete_button.setToolTip("Supprimer")
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: red;
                    font-size: 16px;
                    border: none;
                }
                QPushButton:hover {
                    color: darkred;
                }
            """)
            delete_button.clicked.connect(lambda _, p=path, i=item: self.delete_path(p, i))
            self.tree.setItemWidget(item, 3, delete_button)

        msg = f"📂 Contenu de : {self.current_folder}"
        if duration > 0:
            msg += f" | Analyse terminée en {duration:.2f} s"
        if count > 0:
            msg += f" | {count} élément(s)"
        self.label.setText(msg)

    def delete_path(self, path, item):
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Voulez-vous vraiment supprimer :\n{path} ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)

                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

                if self.current_folder in self.scan_cache:
                    self.scan_cache[self.current_folder].pop(path, None)

                self.label.setText(f"{path} supprimé avec succès.")
                self.show_mosaic()
                self.update_disk_usage_bar(self.current_folder)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la suppression : {e}")

    def on_item_clicked(self, item, column):
        full_path = item.data(1, Qt.UserRole)
        if full_path and os.path.isdir(full_path):
            self.start_scan(full_path)

    def show_mosaic(self):
        if hasattr(self, 'last_results') and self.last_results:
            filtered = [(p, s) for p, s in self.last_results.items() if s > 0]
            if not filtered:
                self.label.setText("Aucun fichier avec une taille non nulle.")
                return
            max_size = max(s for _, s in filtered)
            threshold = max_size * 0.01
            filtered = [(p, s) for p, s in filtered if s >= threshold]
            if not filtered:
                self.label.setText("Aucun élément significatif à afficher (tous < 1%).")
                return
            sizes = [s for _, s in filtered]
            labels = [
                f"{os.path.basename(p) or p}\n{human_readable_size(s)}"
                for p, s in filtered
            ]
            if self.canvas:
                self.layout().removeWidget(self.canvas)
                self.canvas.setParent(None)
            self.canvas = TreemapCanvas(sizes, labels)
            self.layout().addWidget(self.canvas)
        else:
            self.label.setText("Aucune donnée à afficher.")

    def clear_breadcrumb(self):
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def build_breadcrumb(self, path):
        self.clear_breadcrumb()
        path = os.path.abspath(path)
        parts = []
        cumulative_path = path
        while True:
            parts.insert(0, (os.path.basename(cumulative_path) or cumulative_path, cumulative_path))
            parent = os.path.dirname(cumulative_path)
            if parent == cumulative_path:
                break
            cumulative_path = parent
        for i, (label, full_path) in enumerate(parts):
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setStyleSheet("text-decoration: underline; color: blue; background: transparent; border: none;")
            btn.clicked.connect(lambda _, p=full_path: self.start_scan(p))
            self.breadcrumb_layout.addWidget(btn)
            if i < len(parts) - 1:
                self.breadcrumb_layout.addWidget(QLabel("➜"))


# --- Lancer l'application ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DiskAnalyzerApp()
    window.show()
    sys.exit(app.exec())
