; Inno Setup script — wraps the built J.A.R.V.I.S. exe into a Windows installer.
; Compiled in CI:  ISCC /Odist deploy/desktop/installer.iss
; The exe path and version come from environment variables set by the workflow.

#define AppName "J.A.R.V.I.S."
#define AppPublisher "J.A.R.V.I.S."
#define AppExe GetEnv("JARVIS_EXE")
#define AppVersion GetEnv("JARVIS_VERSION")
#if AppVersion == ""
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{9E5D2A2C-7A1B-4E9F-9C1E-J4RV1S000001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\JARVIS
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputBaseFilename=JARVIS-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName={#AppName}

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#AppExe}"; DestDir: "{app}"; DestName: "JARVIS.exe"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\JARVIS.exe"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\JARVIS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\JARVIS.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
