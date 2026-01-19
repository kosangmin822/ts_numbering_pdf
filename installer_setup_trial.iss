; Inno Setup 설치 스크립트 (트라이얼 버전)
; TS Numbering for PDF v1.29_trial 설치 프로그램

#define MyAppName "TS Numbering for PDF"
#define MyAppVersion "1.52"
#define MyAppPublisher "Taesung Engineering"
#define MyAppURL "https://www.taesung.co.kr"
#define MyAppExeName "TS_Numbering_PDF_Trial.exe"
#define MyAppId "{{B2C3D4E5-F6G7-8901-BCDE-F23456789012}"

[Setup]
; 설치 프로그램 기본 정보
AppId={#MyAppId}
AppName={#MyAppName} (Trial)
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}_trial
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName} Trial
DefaultGroupName={#MyAppName} Trial
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=README
OutputDir=installer
OutputBaseFilename=TS_Numbering_PDF_Trial_Setup_v1.52
SetupIconFile=resources\icons\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; 메인 실행 파일 (트라이얼 버전)
Source: "dist\TS_Numbering_PDF_Trial\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 리소스 폴더 전체 복사 (아이콘, 이미지, 데이터 등)
Source: "resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs

; README 및 라이선스 파일
Source: "README"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName} (Trial)"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icons\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName} (Trial)}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} (Trial)"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\resources\icons\icon.ico"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName} (Trial)"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; IconFilename: "{app}\resources\icons\icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}} (Trial)"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\resources"
Type: filesandordirs; Name: "{app}"

[Code]
// 사용자 정의 코드 (필요시 추가)

