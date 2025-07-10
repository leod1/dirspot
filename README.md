# DIRSPOT - Analyseur de disque

DIRSPOT est une application graphique permettant d'analyser l'utilisation de l'espace disque d'un dossier, d'afficher la taille des fichiers et dossiers sous forme de liste et de mosaïque (treemap), et de supprimer facilement des éléments volumineux.

## Fonctionnalités principales
- Analyse récursive de l'espace disque d'un dossier
- Affichage graphique (treemap) des tailles de fichiers/dossiers
- Navigation interactive dans l'arborescence
- Suppression de fichiers et dossiers directement depuis l'interface
- Indicateur d'utilisation du disque

## Prérequis
- Python 3.8 ou supérieur
- Windows (testé sous Windows, peut fonctionner sous Linux/Mac avec adaptation du backend Qt)
- Dépendances Python :
  - PySide6
  - matplotlib
  - squarify

Installez les dépendances avec :

```powershell
pip install -r requirements.txt
```

Ou individuellement :

```powershell
pip install PySide6 matplotlib squarify
```

## Lancer l'application en mode développement

```powershell
py gui.py
```

## Section Build

Pour générer un exécutable autonome (onefile) de l'application, utilisez PyInstaller avec la commande suivante :

```powershell
py -m PyInstaller --onefile --exclude-module PyQt5 .\gui.py
```

- L'option `--onefile` crée un seul fichier exécutable.
- L'option `--exclude-module PyQt5` permet d'éviter les conflits si PyQt5 est installé (l'application utilise PySide6).
- Le fichier exécutable sera généré dans le dossier `dist/`.

## Structure du projet

- `gui.py` : Interface graphique principale
- `scanner.py` : Analyse récursive des dossiers
- `analyzer.py` : Fonctions utilitaires de tri/filtrage
- `ui.py` : Fonctions utilitaires d'affichage
- `main.py` : (optionnel) Point d'entrée alternatif

## Auteurs
- Projet réalisé par DEVAUX Léo

## Licence
Ce projet est open-source, sous licence MIT.
