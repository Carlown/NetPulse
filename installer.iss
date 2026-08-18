; NetPulse 安装程序脚本（Inno Setup 7）
#define MyAppName "NetPulse"
#define MyAppVersion "1.0.3"
#define MyAppPublisher "NetPulse"
#define MyAppExeName "NetPulse.exe"

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
OutputBaseFilename=NetPulse-Setup-1.0.3
SetupIconFile=app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "chinese"; MessagesFile: "compiler:Default.isl"

[Messages]
; 覆盖为简体中文
SetupAppTitle=安装 - NetPulse
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=此向导将引导您在电脑上安装 [name/{#MyAppVersion}]。%n%n建议在继续之前关闭其他应用程序。
WizardReady=准备安装
ReadyLabel1=安装向导已准备好把 [name] 安装到您的电脑。
ReadyLabel2b=点击“安装”继续，或点击“上一步”检查或修改设置。
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonFinish=完成(&F)
ButtonCancel=取消
SelectDirDesc=选择安装位置
SelectDirLabel3=安装向导将把 [name] 安装到以下文件夹。
SelectDirBrowseLabel=点击“下一步”继续。若要更换文件夹，请点击“浏览”。
InstallingLabel=正在安装 [name]，请稍候…
FinishedHeadingLabel=[name] 安装完成
FinishedLabelNoIcons=安装向导已在您的电脑上安装 [name]。点击“完成”退出向导。
ExitSetupTitle=退出安装
ExitSetupMessage=安装尚未完成。如果现在退出，程序将不会被安装。%n%n您可以稍后再次运行安装向导完成安装。%n%n确定退出安装吗？

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(&D)"; GroupDescription: "附加任务："

[Files]
Source: "dist\NetPulse.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\NetPulse"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\NetPulse"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "运行 NetPulse"; Flags: nowait postinstall skipifsilent
