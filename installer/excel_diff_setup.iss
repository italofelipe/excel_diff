[Setup]
AppName=Excel Diff
AppVersion=1.0.0
AppPublisher=Excel Diff
DefaultDirName={autopf}\ExcelDiff
DefaultGroupName=Excel Diff
OutputDir=Output
OutputBaseFilename=ExcelDiff_Instalador_v1.0.0
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayName=Excel Diff
UninstallDisplayIcon={app}\ExcelDiff.exe

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; GroupDescription: "Ícones adicionais:"; Flags: unchecked

[Files]
Source: "..\dist\ExcelDiff\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Excel Diff"; Filename: "{app}\ExcelDiff.exe"
Name: "{group}\Desinstalar Excel Diff"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Excel Diff"; Filename: "{app}\ExcelDiff.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ExcelDiff.exe"; Description: "Abrir Excel Diff"; Flags: nowait postinstall skipifsilent
