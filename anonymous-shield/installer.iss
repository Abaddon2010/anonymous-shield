; Anonymous Shield — instalador Inno Setup
; Requer: Inno Setup 6 + dist\AnonymousShield.exe já construído (PyInstaller).
; Compilar: iscc installer.iss
#define MyAppName "Anonymous Shield"
#define MyAppVersion "1.8.4"
#define MyAppPublisher "Anonymous Shield"
#define MyAppURL "https://www.torproject.org/"
#define MyAppExeName "AnonymousShield.exe"

[Setup]
AppId={{8F3A2B1C-7D4E-4A5F-9C6B-ANONSHIELD01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\Anonymous Shield
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer-out
OutputBaseFilename=AnonymousShield-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\*"; DestDir: "{app}\vendor"; Flags: ignoreversion recursesubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE-APACHE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
