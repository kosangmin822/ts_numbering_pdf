"""
PyInstaller를 사용하여 설치파일을 생성하는 스크립트
"""
import PyInstaller.__main__
import os

# 프로젝트 루트 디렉토리
project_root = os.path.dirname(os.path.abspath(__file__))

# PyInstaller 옵션 설정
PyInstaller.__main__.run([
    'main.py',
    '--name=TS_Numbering_PDF',
    '--onefile',  # 단일 실행 파일로 생성
    '--windowed',  # 콘솔 창 숨기기 (GUI 애플리케이션)
    '--icon=resources/icons/icon.ico',  # 아이콘 파일
    '--add-data=resources;resources',  # 리소스 폴더 포함
    '--hidden-import=PySide6',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets',
    '--hidden-import=PySide6.QtMultimedia',
    '--hidden-import=fitz',  # PyMuPDF
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=pyvista',
    '--hidden-import=trimesh',
    '--hidden-import=vtk',
    '--hidden-import=matplotlib',
    '--hidden-import=scipy',
    '--hidden-import=PIL',
    '--collect-all=pyvista',  # pyvista의 모든 데이터 파일 수집
    '--collect-all=vtk',  # vtk의 모든 데이터 파일 수집
    '--noconfirm',  # 기존 빌드 덮어쓰기
    '--clean',  # 빌드 전 캐시 정리
])

