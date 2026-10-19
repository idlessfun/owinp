#define MyAppName "OWINP"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "OWINP Contributors"
#define MyAppURL "https://github.com/idlessfun/owinp"
#define MyAppExeName "OWINP.exe"

[Setup]
AppId={{B3C2A9E0-6D9F-4F5A-9B8C-7E6D5C4B3A2F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany=OWINP Contributors
VersionInfoDescription=OWINP Setup
VersionInfoProductName=OWINP
VersionInfoProductVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
OutputDir=build
OutputBaseFilename=OWINP-Setup-{#MyAppVersion}
SetupIconFile=app\resources\icon.ico
Compression=zip
SolidCompression=no
WizardStyle=modern
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
; No registry writes at all: uninstall via the Start Menu shortcut.
; This also avoids "access denied" on locked-down machines.
CreateUninstallRegKey=no
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "build\OWINP-release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent