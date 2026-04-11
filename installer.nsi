; Turn off old selected section
; 26 06 2015: Fadiga Ibrahima

; -------------------------------
; Start

  !define MUI_PRODUCT "MPayments"
  ; Doit correspondre au nom du .exe produit par PyInstaller (mpayment_wind.spec)
  !define MUI_FILE "MPayments"
  !define MUI_VERSION "26.4 BK"
  ; Clé unique pour installations côte-à-côte (évite d'écraser l'ancienne)
  !define MUI_PRODUCT_KEY "${MUI_PRODUCT}-${MUI_VERSION}"
  !define MUI_BRANDINGTEXT "${MUI_PRODUCT} ${MUI_VERSION}"
  !define IMAGES "images"
  !define CIMAGES "cimages"
  !define MEDIA "static"
  ; Les icônes Common (cimages) sont incluses dans dist\MPayments\_internal (PyInstaller) ;
  ; ne plus copier depuis un chemin machine absolu.
  ;CRCCheck On

  !include "${NSISDIR}\Contrib\Modern UI\System.nsh"


;---------------------------------
;General

  OutFile "Install-${MUI_PRODUCT}-${MUI_VERSION}.exe"
  ShowInstDetails "nevershow"
  ShowUninstDetails "nevershow"
  ;SetCompressor off

  ; Icône de l’assistant d’installation (fichier à côté du .nsi ou chemin explicite)
  !define MUI_ICON "static\images\logo.ico"
  !define MUI_UNICON "static\images\logo.ico"
  !define MUI_SPECIALBITMAP "Bitmap.bmp"


;--------------------------------
;Folder selection page

  ; Dossier versionné pour permettre plusieurs versions en parallèle
  InstallDir "C:\${MUI_PRODUCT_KEY}"


;--------------------------------
;Data

    ;LicenseData "README.txt"


;--------------------------------
;Installer Sections
;Section "install" Installation info
Section "install"

;Add files
  SetOutPath "$INSTDIR"

  ;File "${MUI_FILE}.exe"
  ;File "README.txt"

  ; Après : pyinstaller --noconfirm mpayment_wind.spec  (dossier dist\MPayments)
  File /r "dist\MPayments\*.*"
  File /nonfatal "ressources\*.dll"
  File /r "${MEDIA}\${IMAGES}"

; Raccourcis : icône = l’exécutable (PyInstaller embarque logo.ico dans MPayments.exe).
; Ne pas utiliser $INSTDIR\static\images\ : en onedir les datas sont sous _internal\.
  !define SHORTCUT_ICON_EXE "$INSTDIR\${MUI_FILE}.exe"

;create desktop shortcut (versionné)
  CreateShortCut "$DESKTOP\${MUI_PRODUCT} ${MUI_VERSION}.lnk" "$INSTDIR\${MUI_FILE}.exe" "" "${SHORTCUT_ICON_EXE}" 0

;create start-menu items (versionné)
  CreateDirectory "$SMPROGRAMS\${MUI_PRODUCT} ${MUI_VERSION}"
  CreateShortCut "$SMPROGRAMS\${MUI_PRODUCT} ${MUI_VERSION}\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "${SHORTCUT_ICON_EXE}" 0
  CreateShortCut "$SMPROGRAMS\${MUI_PRODUCT} ${MUI_VERSION}\${MUI_PRODUCT}.lnk" "$INSTDIR\${MUI_FILE}.exe" "" "${SHORTCUT_ICON_EXE}" 0

;write uninstall information to the registry
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT_KEY}" "DisplayName" "${MUI_PRODUCT} ${MUI_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd


;--------------------------------
;Uninstaller Section
Section "Uninstall"

;Delete Files
;  RMDir /r "$INSTDIR\*.*"

;Remove the installation directory
;  RMDir "$INSTDIR"

# now delete installed file
delete $INSTDIR\*.exe
delete $INSTDIR\*.dll
delete $INSTDIR\*.lib
delete $INSTDIR\*.zip
delete $INSTDIR\*.pdf
delete $INSTDIR\*.pyd

RMDir /r $INSTDIR\build
RMDir /r $INSTDIR\${MEDIA}
RMDir /r $INSTDIR\${CIMAGES}
RMDir /r $INSTDIR\dist
RMDir /r $INSTDIR\tcl

;Delete Start Menu Shortcuts
  Delete "$DESKTOP\${MUI_PRODUCT} ${MUI_VERSION}.lnk"
  Delete "$SMPROGRAMS\${MUI_PRODUCT} ${MUI_VERSION}\*.*"
  RmDir  "$SMPROGRAMS\${MUI_PRODUCT} ${MUI_VERSION}"

;Delete Uninstaller And Unistall Registry Entries
  DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\${MUI_PRODUCT_KEY}"
  DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT_KEY}"

SectionEnd

;--------------------------------
Function .onInstSuccess
  ;MessageBox MB_OK "Vous avez installé le ${MUI_PRODUCT}.Utilise son icon sur le ;bureau pour lancer le program."

   SetOutPath $INSTDIR
   ExecShell "" '"$INSTDIR\${MUI_FILE}.exe"'
FunctionEnd

Function un.onUninstSuccess
  MessageBox MB_OK "You have successfully uninstalled ${MUI_PRODUCT}."
FunctionEnd

;eof