; NetPulse Installer Script (Inno Setup 7)
; 中英双语安装程序
#define MyAppName "NetPulse"
#define MyAppVersion "1.0.7"
#define MyAppPublisher "NetPulse"
#define MyAppExeName "NetPulse.exe"
#define MyAppDirName "NetPulse"

[Setup]
AppId={{8F4A2C1E-9B3D-4E6A-B5C7-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=installer
OutputBaseFilename=NetPulse-Setup-1.0.7
SetupIconFile=app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[CustomMessages]
english.RunApp=Run NetPulse
chinesesimplified.RunApp=运行 NetPulse
english.DesktopIcon=Create a desktop shortcut
chinesesimplified.DesktopIcon=创建桌面快捷方式(&D)
english.AdditionalTasks=Additional tasks:
chinesesimplified.AdditionalTasks=附加任务：
english.ProgramComment=NetPulse Network Stress Testing Tool
chinesesimplified.ProgramComment=NetPulse 网络压力测试工具

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:AdditionalTasks}"

[Files]
Source: "dist\{#MyAppDirName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\NetPulse"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "{cm:ProgramComment}"
Name: "{autodesktop}\NetPulse"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "{cm:ProgramComment}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:RunApp}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
