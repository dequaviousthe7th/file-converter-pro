; File Converter Pro - Inno Setup Script
; Packages compiled .exe applications into a standard Windows installer

#define MyAppName "File Converter Pro"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Dequavious"
#define MyAppURL "https://github.com/dequaviousthe7th"

[Setup]
AppId={{E8F3A1B2-5C7D-4E9F-B6A0-1D2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
InfoBeforeFile=info_before.txt
OutputDir=..\dist
OutputBaseFilename=FCP-Setup
SetupIconFile=..\assets\logo.ico
UninstallDisplayIcon={app}\assets\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableWelcomePage=no
VersionInfoVersion=2.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoCopyright=Copyright (c) 2025 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to [name] Setup
WelcomeLabel2=This will install [name/ver] on your computer.%n%n200+ conversion paths across 55+ file formats.%nDocuments, images, audio, video, spreadsheets, and config files.%n%n100%% local - no files are ever uploaded anywhere.%n%nIt is recommended that you close all other applications before continuing.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Advanced UI (compiled exe + all dependencies)
Source: "..\dist\File Converter Pro\*"; DestDir: "{app}\Advanced"; Flags: ignoreversion recursesubdirs createallsubdirs

; Simple UI (compiled exe + all dependencies)
Source: "..\dist\File Converter Pro Simple\*"; DestDir: "{app}\Simple"; Flags: ignoreversion recursesubdirs createallsubdirs

; Assets (for icon references)
Source: "..\assets\logo.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\logo.png"; DestDir: "{app}\assets"; Flags: ignoreversion

; License
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\converted"

[Icons]
; Start Menu - both UIs always available for easy switching
Name: "{group}\{#MyAppName} (Advanced)"; Filename: "{app}\Advanced\File Converter Pro.exe"; WorkingDir: "{app}\Advanced"; IconFilename: "{app}\assets\logo.ico"; Comment: "Modern dark theme with tabs, history, settings, and batch conversion"
Name: "{group}\{#MyAppName} (Simple)"; Filename: "{app}\Simple\File Converter Pro Simple.exe"; WorkingDir: "{app}\Simple"; IconFilename: "{app}\assets\logo.ico"; Comment: "Clean, lightweight classic interface for quick conversions"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop - based on UI selection in custom page
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Advanced\File Converter Pro.exe"; WorkingDir: "{app}\Advanced"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon; Check: IsAdvancedUI
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Simple\File Converter Pro Simple.exe"; WorkingDir: "{app}\Simple"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon; Check: IsSimpleUI

[Run]
; Launch options on finish page
Filename: "{app}\Advanced\File Converter Pro.exe"; Description: "Launch {#MyAppName} (Advanced UI)"; WorkingDir: "{app}\Advanced"; Flags: nowait postinstall skipifsilent; Check: IsAdvancedUI
Filename: "{app}\Simple\File Converter Pro Simple.exe"; Description: "Launch {#MyAppName} (Simple UI)"; WorkingDir: "{app}\Simple"; Flags: nowait postinstall skipifsilent; Check: IsSimpleUI

[UninstallDelete]
Type: filesandordirs; Name: "{app}\converted"
Type: filesandordirs; Name: "{app}\Advanced"
Type: filesandordirs; Name: "{app}\Simple"

[Code]
var
  UIPage: TWizardPage;
  ToolsPage: TWizardPage;
  AdvancedButton: TNewRadioButton;
  SimpleButton: TNewRadioButton;
  FFmpegCheck: TNewCheckBox;
  PandocCheck: TNewCheckBox;

function IsAdvancedUI: Boolean;
begin
  Result := AdvancedButton.Checked;
end;

function IsSimpleUI: Boolean;
begin
  Result := SimpleButton.Checked;
end;

function IsFFmpegInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c ffmpeg -version >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function IsPandocInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c pandoc --version >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure InstallOptionalTools;
var
  ResultCode: Integer;
begin
  if FFmpegCheck.Checked and (not IsFFmpegInstalled) then
  begin
    WizardForm.StatusLabel.Caption := 'Installing ffmpeg (this may take a minute)...';
    Exec('cmd.exe', '/c winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;

  if PandocCheck.Checked and (not IsPandocInstalled) then
  begin
    WizardForm.StatusLabel.Caption := 'Installing Pandoc (this may take a minute)...';
    Exec('cmd.exe', '/c winget install --id JohnMacFarlane.Pandoc -e --accept-package-agreements --accept-source-agreements', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    InstallOptionalTools;
  end;
end;

procedure CreateUIPage;
var
  TitleLabel: TNewStaticText;
  Separator1: TBevel;
  Separator2: TBevel;
  AdvancedDesc: TNewStaticText;
  AdvancedFeatures: TNewStaticText;
  SimpleDesc: TNewStaticText;
  SimpleFeatures: TNewStaticText;
  NoteLabel: TNewStaticText;
begin
  UIPage := CreateCustomPage(wpLicense,
    'Choose Your Default Interface',
    'Both UIs are always installed. Select which one to use as your default.');

  TitleLabel := TNewStaticText.Create(UIPage);
  TitleLabel.Parent := UIPage.Surface;
  TitleLabel.Caption := 'File Converter Pro ships with two UI modes:';
  TitleLabel.Font.Size := 10;
  TitleLabel.Left := 0;
  TitleLabel.Top := 8;
  TitleLabel.Width := UIPage.SurfaceWidth;

  // === Advanced UI ===
  AdvancedButton := TNewRadioButton.Create(UIPage);
  AdvancedButton.Parent := UIPage.Surface;
  AdvancedButton.Caption := 'Advanced UI  -  Modern Dark Theme';
  AdvancedButton.Font.Size := 10;
  AdvancedButton.Font.Style := [fsBold];
  AdvancedButton.Left := 0;
  AdvancedButton.Top := 48;
  AdvancedButton.Width := UIPage.SurfaceWidth;
  AdvancedButton.Height := 24;
  AdvancedButton.Checked := True;

  AdvancedDesc := TNewStaticText.Create(UIPage);
  AdvancedDesc.Parent := UIPage.Surface;
  AdvancedDesc.Caption := 'Best for power users and batch workflows.';
  AdvancedDesc.Left := 20;
  AdvancedDesc.Top := 74;
  AdvancedDesc.Width := UIPage.SurfaceWidth - 20;
  AdvancedDesc.Font.Color := clGray;

  AdvancedFeatures := TNewStaticText.Create(UIPage);
  AdvancedFeatures.Parent := UIPage.Surface;
  AdvancedFeatures.Caption :=
    '    - Modern dark studio theme (CustomTkinter)' + #13#10 +
    '    - Tab navigation with dedicated batch conversion page' + #13#10 +
    '    - Full conversion history tracking' + #13#10 +
    '    - Configurable output folder, image quality, audio bitrate' + #13#10 +
    '    - Drag and drop support';
  AdvancedFeatures.Left := 20;
  AdvancedFeatures.Top := 94;
  AdvancedFeatures.Width := UIPage.SurfaceWidth - 20;
  AdvancedFeatures.Height := 80;
  AdvancedFeatures.Font.Color := clGray;

  Separator1 := TBevel.Create(UIPage);
  Separator1.Parent := UIPage.Surface;
  Separator1.Left := 0;
  Separator1.Top := 182;
  Separator1.Width := UIPage.SurfaceWidth;
  Separator1.Height := 2;
  Separator1.Shape := bsTopLine;

  // === Simple UI ===
  SimpleButton := TNewRadioButton.Create(UIPage);
  SimpleButton.Parent := UIPage.Surface;
  SimpleButton.Caption := 'Simple UI  -  Classic Lightweight';
  SimpleButton.Font.Size := 10;
  SimpleButton.Font.Style := [fsBold];
  SimpleButton.Left := 0;
  SimpleButton.Top := 196;
  SimpleButton.Width := UIPage.SurfaceWidth;
  SimpleButton.Height := 24;
  SimpleButton.Checked := False;

  SimpleDesc := TNewStaticText.Create(UIPage);
  SimpleDesc.Parent := UIPage.Surface;
  SimpleDesc.Caption := 'Best for quick single-file conversions.';
  SimpleDesc.Left := 20;
  SimpleDesc.Top := 222;
  SimpleDesc.Width := UIPage.SurfaceWidth - 20;
  SimpleDesc.Font.Color := clGray;

  SimpleFeatures := TNewStaticText.Create(UIPage);
  SimpleFeatures.Parent := UIPage.Surface;
  SimpleFeatures.Caption :=
    '    - Clean, lightweight classic interface (Standard Tkinter)' + #13#10 +
    '    - Batch mode toggle for multiple files' + #13#10 +
    '    - Drag and drop support' + #13#10 +
    '    - Kill button to cancel any conversion';
  SimpleFeatures.Left := 20;
  SimpleFeatures.Top := 242;
  SimpleFeatures.Width := UIPage.SurfaceWidth - 20;
  SimpleFeatures.Height := 65;
  SimpleFeatures.Font.Color := clGray;

  Separator2 := TBevel.Create(UIPage);
  Separator2.Parent := UIPage.Surface;
  Separator2.Left := 0;
  Separator2.Top := 316;
  Separator2.Width := UIPage.SurfaceWidth;
  Separator2.Height := 2;
  Separator2.Shape := bsTopLine;

  NoteLabel := TNewStaticText.Create(UIPage);
  NoteLabel.Parent := UIPage.Surface;
  NoteLabel.Caption := 'Both UIs are always installed. You can switch anytime via Start Menu shortcuts or the built-in switch button.';
  NoteLabel.Left := 0;
  NoteLabel.Top := 330;
  NoteLabel.Width := UIPage.SurfaceWidth;
  NoteLabel.Font.Style := [fsItalic];
  NoteLabel.Font.Color := clGray;
end;

procedure CreateToolsPage;
var
  TitleLabel: TNewStaticText;
  Separator: TBevel;
  FFmpegTitle: TNewStaticText;
  FFmpegDesc: TNewStaticText;
  FFmpegStatus: TNewStaticText;
  PandocTitle: TNewStaticText;
  PandocDesc: TNewStaticText;
  PandocStatus: TNewStaticText;
  NoteLabel: TNewStaticText;
  FFmpegInstalled: Boolean;
  PandocInstalled: Boolean;
begin
  ToolsPage := CreateCustomPage(UIPage.ID,
    'Optional Tools',
    'These tools enable additional conversion types. You can always install them later.');

  TitleLabel := TNewStaticText.Create(ToolsPage);
  TitleLabel.Parent := ToolsPage.Surface;
  TitleLabel.Caption := 'The app works for most conversions without these. Check the ones you want to install:';
  TitleLabel.Font.Size := 9;
  TitleLabel.Left := 0;
  TitleLabel.Top := 8;
  TitleLabel.Width := ToolsPage.SurfaceWidth;
  TitleLabel.AutoSize := False;
  TitleLabel.Height := 30;
  TitleLabel.WordWrap := True;

  FFmpegInstalled := IsFFmpegInstalled;

  // === FFmpeg ===
  FFmpegCheck := TNewCheckBox.Create(ToolsPage);
  FFmpegCheck.Parent := ToolsPage.Surface;
  FFmpegCheck.Caption := '  Install FFmpeg';
  FFmpegCheck.Font.Size := 10;
  FFmpegCheck.Font.Style := [fsBold];
  FFmpegCheck.Left := 0;
  FFmpegCheck.Top := 48;
  FFmpegCheck.Width := ToolsPage.SurfaceWidth;
  FFmpegCheck.Height := 24;
  if FFmpegInstalled then
    FFmpegCheck.Checked := False
  else
    FFmpegCheck.Checked := True;

  FFmpegDesc := TNewStaticText.Create(ToolsPage);
  FFmpegDesc.Parent := ToolsPage.Surface;
  FFmpegDesc.Caption :=
    'Required for audio and video conversion.' + #13#10 +
    'Formats: MP3, WAV, FLAC, OGG, AAC, M4A, WMA, MP4, AVI, MKV, MOV, WebM, GIF' + #13#10 +
    'Without FFmpeg, audio and video conversions will not work.';
  FFmpegDesc.Left := 28;
  FFmpegDesc.Top := 74;
  FFmpegDesc.Width := ToolsPage.SurfaceWidth - 28;
  FFmpegDesc.Height := 52;
  FFmpegDesc.Font.Color := clGray;

  FFmpegStatus := TNewStaticText.Create(ToolsPage);
  FFmpegStatus.Parent := ToolsPage.Surface;
  FFmpegStatus.Left := 28;
  FFmpegStatus.Top := 128;
  FFmpegStatus.Width := ToolsPage.SurfaceWidth - 28;
  if FFmpegInstalled then
  begin
    FFmpegStatus.Caption := 'Already installed on this system.';
    FFmpegStatus.Font.Color := $0000AA00;
    FFmpegCheck.Enabled := False;
  end
  else
  begin
    FFmpegStatus.Caption := 'Not detected. Will be installed via winget.';
    FFmpegStatus.Font.Color := $000060D0;
  end;

  Separator := TBevel.Create(ToolsPage);
  Separator.Parent := ToolsPage.Surface;
  Separator.Left := 0;
  Separator.Top := 158;
  Separator.Width := ToolsPage.SurfaceWidth;
  Separator.Height := 2;
  Separator.Shape := bsTopLine;

  PandocInstalled := IsPandocInstalled;

  // === Pandoc ===
  PandocCheck := TNewCheckBox.Create(ToolsPage);
  PandocCheck.Parent := ToolsPage.Surface;
  PandocCheck.Caption := '  Install Pandoc';
  PandocCheck.Font.Size := 10;
  PandocCheck.Font.Style := [fsBold];
  PandocCheck.Left := 0;
  PandocCheck.Top := 174;
  PandocCheck.Width := ToolsPage.SurfaceWidth;
  PandocCheck.Height := 24;
  if PandocInstalled then
    PandocCheck.Checked := False
  else
    PandocCheck.Checked := True;

  PandocDesc := TNewStaticText.Create(ToolsPage);
  PandocDesc.Parent := ToolsPage.Surface;
  PandocDesc.Caption :=
    'Required for advanced document conversion.' + #13#10 +
    'Improves: PDF, DOCX, Markdown, HTML, EPUB, RTF conversions' + #13#10 +
    'Without Pandoc, some document conversions may produce lower quality results.';
  PandocDesc.Left := 28;
  PandocDesc.Top := 200;
  PandocDesc.Width := ToolsPage.SurfaceWidth - 28;
  PandocDesc.Height := 52;
  PandocDesc.Font.Color := clGray;

  PandocStatus := TNewStaticText.Create(ToolsPage);
  PandocStatus.Parent := ToolsPage.Surface;
  PandocStatus.Left := 28;
  PandocStatus.Top := 254;
  PandocStatus.Width := ToolsPage.SurfaceWidth - 28;
  if PandocInstalled then
  begin
    PandocStatus.Caption := 'Already installed on this system.';
    PandocStatus.Font.Color := $0000AA00;
    PandocCheck.Enabled := False;
  end
  else
  begin
    PandocStatus.Caption := 'Not detected. Will be installed via winget.';
    PandocStatus.Font.Color := $000060D0;
  end;

  NoteLabel := TNewStaticText.Create(ToolsPage);
  NoteLabel.Parent := ToolsPage.Surface;
  NoteLabel.Caption := 'These are free, open-source tools installed via Windows Package Manager (winget). You can uninstall them anytime from Add/Remove Programs.';
  NoteLabel.Left := 0;
  NoteLabel.Top := 300;
  NoteLabel.Width := ToolsPage.SurfaceWidth;
  NoteLabel.AutoSize := False;
  NoteLabel.Height := 40;
  NoteLabel.WordWrap := True;
  NoteLabel.Font.Style := [fsItalic];
  NoteLabel.Font.Color := clGray;
end;

procedure InitializeWizard();
begin
  CreateUIPage;
  CreateToolsPage;
end;
