@echo off
chcp 65001
echo 트라이얼 정보를 초기화합니다...
echo (레지스트리 키 삭제: HKEY_CURRENT_USER\SOFTWARE\TS_Numbering_PDF)

reg delete "HKEY_CURRENT_USER\SOFTWARE\TS_Numbering_PDF" /f

if %errorlevel% == 0 (
    echo.
    echo [성공] 트라이얼 정보가 초기화되었습니다.
) else (
    echo.
    echo [실패] 트라이얼 정보를 찾을 수 없거나 삭제에 실패했습니다.
    echo (이미 삭제되었거나 권한이 부족할 수 있습니다.)
)

echo.
pause
