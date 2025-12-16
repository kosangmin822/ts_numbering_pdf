# TS Numbering for PDF 설치 파일 생성 가이드

## 개요
이 문서는 Inno Setup을 사용하여 TS Numbering for PDF의 Windows 설치 파일(.exe)을 만드는 방법을 설명합니다.

## 사전 준비

### 1. Inno Setup 설치
1. Inno Setup 다운로드: https://jrsoftware.org/isdl.php
2. 최신 버전(6.x 이상) 설치
3. 설치 시 "Inno Setup Preprocessor" 옵션도 함께 설치

### 2. 빌드 옵션 변경
현재는 단일 실행 파일(`--onefile`)로 빌드되어 있지만, 설치 파일을 만들기 위해서는 폴더 형태(`--onedir`)로 빌드하는 것이 더 좋습니다.

## 설치 파일 생성 방법

### 방법 1: Inno Setup Compiler 사용 (GUI)

1. **Inno Setup Compiler 실행**
2. **File → Open** 메뉴에서 `installer_setup.iss` 파일 열기
3. **Build → Compile** 메뉴 클릭 (또는 F9)
4. 생성된 설치 파일 위치: `installer\TS_Numbering_PDF_Setup_v7.00_stable.exe`

### 방법 2: 명령줄 사용

```bash
# Inno Setup Compiler 경로로 이동 (기본 설치 경로)
cd "C:\Program Files (x86)\Inno Setup 6"

# 설치 스크립트 컴파일
ISCC.exe "C:\ts_numbering_pdf\installer_setup.iss"
```

### 방법 3: Python 스크립트 사용

```python
import subprocess
import os

inno_setup_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
script_path = os.path.abspath("installer_setup.iss")

if os.path.exists(inno_setup_path):
    subprocess.run([inno_setup_path, script_path])
else:
    print("Inno Setup을 찾을 수 없습니다. 경로를 확인하세요.")
```

## 설치 파일 구성

### 포함되는 내용
- **실행 파일**: `TS_Numbering_PDF.exe`
- **리소스 폴더**: `resources\` (아이콘, 이미지, 데이터 파일 등)
- **문서**: README, LICENSE

### 설치 위치
- 기본 설치 경로: `C:\Program Files\TS Numbering for PDF\`
- 사용자 데이터: 각 사용자의 AppData 폴더

### 설치 옵션
- 바탕화면 바로가기 (선택)
- 빠른 실행 바로가기 (선택)
- 시작 메뉴 항목 (기본)

## 리소스 파일 수정

설치 후에도 리소스 파일을 쉽게 수정할 수 있도록 `resources` 폴더가 별도로 포함됩니다:

- **아이콘 변경**: `resources\icons\` 폴더의 파일 교체
- **사격모드 효과**: `resources\ester_egg\` 폴더의 파일 교체
- **데이터 파일**: `resources\data\` 폴더의 파일 수정

## 주의사항

1. **빌드 모드 변경 필요**
   - 현재 `--onefile` 모드로 빌드되어 있음
   - 설치 파일을 만들려면 `--onedir` 모드로 변경하는 것이 좋음
   - 또는 현재 방식 유지 가능 (단일 실행 파일 포함)

2. **리소스 파일 경로**
   - 설치 후 리소스 파일 경로가 변경될 수 있음
   - `resource_path()` 함수가 올바르게 작동하는지 확인 필요

3. **관리자 권한**
   - Program Files에 설치하려면 관리자 권한 필요
   - 사용자 폴더에 설치하려면 `PrivilegesRequired=lowest`로 변경

## 빌드 모드 변경 (선택사항)

폴더 형태로 빌드하려면 `TS_Numbering_PDF.spec` 파일을 수정:

```python
# --onefile 대신 --onedir 사용
exe = EXE(
    ...
    # onefile 옵션 제거 또는 False로 설정
)
```

또는 새로운 spec 파일 생성:

```bash
pyinstaller --onedir --windowed --icon=resources/icons/icon.ico --add-data="resources;resources" main.py
```

## 문제 해결

### Inno Setup을 찾을 수 없을 때
- 설치 경로 확인: `C:\Program Files (x86)\Inno Setup 6\`
- 또는 환경 변수 PATH에 추가

### 리소스 파일을 찾을 수 없을 때
- 설치 후 실행 파일과 같은 폴더에 `resources` 폴더가 있는지 확인
- `resource_path()` 함수가 올바른 경로를 반환하는지 확인

