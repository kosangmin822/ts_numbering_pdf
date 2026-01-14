
import PyInstaller.__main__
import os
import shutil

def build_official():
    print("Building Official Version...")
    PyInstaller.__main__.run([
        'main.py',
        '--name=TS_Numbering_PDF',
        '--onefile',
        '--windowed',
        '--icon=resources/icons/icon.ico',
        '--add-data=resources;resources',
        '--hidden-import=PySide6',
        '--hidden-import=PySide6.QtCore',
        '--hidden-import=PySide6.QtGui',
        '--hidden-import=PySide6.QtWidgets',
        '--hidden-import=PySide6.QtMultimedia',
        '--hidden-import=pypdfium2',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=pyvista',
        '--hidden-import=trimesh',
        '--hidden-import=vtk',
        '--hidden-import=matplotlib',
        '--hidden-import=scipy',
        '--hidden-import=PIL',
        '--collect-all=pyvista',
        '--collect-all=vtk',
        '--noconfirm',
        '--clean',
        '--noupx',
    ])

def build_trial():
    print("Building Trial Version...")
    PyInstaller.__main__.run([
        'main_trial.py',
        '--name=TS_Numbering_PDF_Trial',
        '--onefile',
        '--windowed',
        '--icon=resources/icons/icon.ico',
        '--add-data=resources;resources',
        '--hidden-import=PySide6',
        '--hidden-import=PySide6.QtCore',
        '--hidden-import=PySide6.QtGui',
        '--hidden-import=PySide6.QtWidgets',
        '--hidden-import=PySide6.QtMultimedia',
        '--hidden-import=pypdfium2',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=pyvista',
        '--hidden-import=trimesh',
        '--hidden-import=vtk',
        '--hidden-import=matplotlib',
        '--hidden-import=scipy',
        '--hidden-import=PIL',
        '--collect-all=pyvista',
        '--collect-all=vtk',
        '--noconfirm',
        '--clean',
        '--noupx',
    ])

if __name__ == "__main__":
    # Clean previous builds if necessary, though --clean handles most
    build_official()
    build_trial()
    print("Build complete. files should be in 'dist' directory.")
