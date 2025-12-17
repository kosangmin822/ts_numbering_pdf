# TS Numbering for PDF 설치파일 생성 가이드

## 개요
이 문서는 PyInstaller를 사용하여 TS Numbering for PDF (v7.00_stable)를 Windows 설치파일(.exe)로 만드는 방법을 설명합니다.

## 사전 준비

### 1. 필요한 패키지 설치
```bash
pip install pyinstaller
```

### 2. PySide6 확인
현재 프로젝트는 PySide6를 사용하고 있으므로, requirements.txt에 다음을 추가해야 합니다:
```
PySide6>=6.0.0
```

## 설치파일 생성 방법

### 방법 1: spec 파일 사용 (권장)

1. **spec 파일로 빌드**
```bash
pyinstaller TS_Numbering_PDF.spec
```

2. **생성된 파일 위치**
- 실행 파일: `dist/TS_Numbering_PDF.exe`

### 방법 2: 명령줄 직접 실행

```bash
pyinstaller --name=TS_Numbering_PDF ^
    --onefile ^
    --windowed ^
    --icon=resources/icons/icon.ico ^
    --add-data="resources;resources" ^
    --hidden-import=PySide6 ^
    --hidden-import=PySide6.QtCore ^
    --hidden-import=PySide6.QtGui ^
    --hidden-import=PySide6.QtWidgets ^
    --hidden-import=PySide6.QtMultimedia ^
    --hidden-import=pypdfium2 ^
    --hidden-import=pandas ^
    --hidden-import=numpy ^
    --hidden-import=pyvista ^
    --hidden-import=trimesh ^
    --hidden-import=vtk ^
    --collect-all=pyvista ^
    --collect-all=vtk ^
    main.py
```

### 방법 3: Python 스크립트 사용

```bash
python build_installer.py
```

## 빌드 옵션 설명

- `--onefile`: 단일 실행 파일로 생성 (배포 시 편리)
- `--windowed` / `--noconsole`: 콘솔 창 숨기기 (GUI 앱)
- `--icon`: 애플리케이션 아이콘 지정
- `--add-data`: 리소스 파일 포함 (형식: "소스경로;대상경로")
- `--hidden-import`: 자동으로 감지되지 않는 모듈 명시
- `--collect-all`: 특정 패키지의 모든 데이터 파일 수집

## 주의사항

1. **VTK/PyVista 관련**
   - VTK와 PyVista는 많은 DLL 파일을 포함하므로 빌드 시간이 오래 걸릴 수 있습니다.
   - `--collect-all=vtk`와 `--collect-all=pyvista` 옵션을 사용하여 필요한 모든 파일을 포함해야 합니다.

2. **리소스 파일**
   - `resources` 폴더의 모든 파일이 실행 파일에 포함되어야 합니다.
   - 아이콘, 이미지, CSV 파일 등이 정상적으로 작동하는지 확인하세요.

3. **테스트**
   - 빌드 후 `dist/TS_Numbering_PDF.exe`를 실행하여 모든 기능이 정상 작동하는지 확인하세요.
   - 특히 3D 뷰어 기능과 리소스 파일 로딩을 확인하세요.

## 문제 해결

### "ModuleNotFoundError" 발생 시
- 해당 모듈을 `--hidden-import`에 추가하세요.
- 또는 `TS_Numbering_PDF.spec` 파일의 `hiddenimports` 리스트에 추가하세요.

### 리소스 파일을 찾을 수 없을 때
- `--add-data` 옵션이 올바르게 설정되었는지 확인하세요.
- Windows에서는 경로 구분자가 `;`입니다 (Linux/Mac은 `:`).

### 실행 파일 크기가 너무 클 때
- `--onefile` 대신 `--onedir`을 사용하면 폴더 형태로 생성됩니다.
- UPX 압축을 사용하려면 `--upx-dir` 옵션을 지정하세요.

## 배포

빌드가 완료되면:
1. `dist/TS_Numbering_PDF.exe` 파일을 배포하세요.
2. 사용자는 Python 설치 없이 이 파일만으로 프로그램을 실행할 수 있습니다.
3. 필요시 설치 프로그램(NSIS, Inno Setup 등)으로 감싸서 배포할 수 있습니다.

