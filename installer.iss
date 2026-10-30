; Script generated for Inno Setup 6
; RuhiPdf Editor - Windows Installer
; Developer: Md. Abdullah Al Mamun

#define MyAppName "RuhiPdf Editor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Md. Abdullah Al Mamun"
#define MyAppURL "https://github.com/Mamuntheprogrammer"
#define MyAppLinkedIn "https://www.linkedin.com/in/mamuntheprogrammer"
#define MyAppEmail "a.a.mamunbu@gmail.com"
#define MyAppExeName "RuhiPdfEditor.exe"

[Setup]
; App Metadata
AppId={{9B7E4A1C-2F5D-4D8A-9A3E-7E1D8B4C0A2E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppLinkedIn}
AppUpdatesURL={#MyAppURL}
AppContact={#MyAppEmail}

; Install Directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Packaging & Compression
OutputDir=dist\installer
OutputBaseFilename=RuhiPdfEditor_Setup_v1.0.0
SetupIconFile=icons\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Privileges (Per-user or all users)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Visual style
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associatepdf"; Description: "Associate {#MyAppName} with PDF files (.pdf)"; GroupDescription: "File Associations:"; Flags: unchecked

[Files]
Source: "dist\RuhiPdfEditor\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\RuhiPdfEditor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Registry]
; PDF File Association (optional task)
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "RuhiPdf.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associatepdf
Root: HKA; Subkey: "Software\Classes\RuhiPdf.Document"; ValueType: string; ValueName: ""; ValueData: "PDF Document"; Flags: uninsdeletekey; Tasks: associatepdf
Root: HKA; Subkey: "Software\Classes\RuhiPdf.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associatepdf
Root: HKA; Subkey: "Software\Classes\RuhiPdf.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associatepdf

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

