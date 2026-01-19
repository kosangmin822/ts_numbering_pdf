; Inno Setup 설치 스크립트
; TS Numbering for PDF v1.29_stable 설치 프로그램

#define MyAppName "TS Numbering for PDF"
#define MyAppVersion "1.51"
#define MyAppPublisher "Taesung Engineering"
#define MyAppURL "https://www.taesung.co.kr"
#define MyAppExeName "TS_Numbering_PDF.exe"
#define MyAppId "{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"

[Setup]
; 설치 프로그램 기본 정보
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}_stable
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=README
OutputDir=installer
OutputBaseFilename=TS_Numbering_PDF_Setup_v1.51_stable
SetupIconFile=resources\icons\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

; 설치 프로그램 아이콘 및 이미지 (선택사항 - 파일이 없으면 주석 처리)
; WizardImageFile=resources\icons\icon.bmp
; WizardSmallImageFile=resources\icons\icon.bmp

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; 메인 실행 파일
Source: "dist\TS_Numbering_PDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 리소스 폴더 전체 복사 (아이콘, 이미지, 데이터 등)
Source: "resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs

; README 및 라이선스 파일
Source: "README"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icons\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\resources\icons\icon.ico"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppName}"; Tasks: quicklaunchicon; IconFilename: "{app}\resources\icons\icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\resources"
Type: filesandordirs; Name: "{app}"

[Code]
// 사용자 정의 코드 (필요시 추가)

