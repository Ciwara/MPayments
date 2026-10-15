; Turn off old selected section
; 26 06 2015: Fadiga Ibrahima

; -------------------------------
; Start

  !define MUI_PRODUCT "Business"
  ; Doit correspondre au nom du .exe produit par PyInstaller (Mpayment_wind.spec)
  !define MUI_FILE "Business"
  !define MUI_VERSION "2.1.3"
  ; Libellé des raccourcis bureau / menu (nom visible pour l’utilisateur)
  !define MUI_SHORTCUT_NAME "Business"
  ; Clé fixe (sans version) : même dossier / même entrée désinstall à chaque mise à jour
  !define MUI_PRODUCT_KEY "${MUI_PRODUCT}"
  !define MUI_BRANDINGTEXT "${MUI_SHORTCUT_NAME} ${MUI_VERSION}"
  !define IMAGES "images"
  !define CIMAGES "cimages"
  !define MEDIA "static"
  ; Les icônes Common (cimages) sont incluses dans dist\Business\_internal (PyInstaller) ;
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

  ; Dossier d'installation fixe (indépendant du numéro de version)
  InstallDir "C:\${MUI_PRODUCT}"


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

  ; Après : pyinstaller --noconfirm Mpayment_wind.spec  (dossier dist\Business)
  File /r "dist\Business\*.*"
  File /nonfatal "ressources\*.dll"
  File /r "${MEDIA}\${IMAGES}"

; Raccourcis : icône = l’exécutable (PyInstaller embarque logo.ico dans Business.exe).
; Ne pas utiliser $INSTDIR\static\images\ : en onedir les datas sont sous _internal\.
  !define SHORTCUT_ICON_EXE "$INSTDIR\${MUI_FILE}.exe"

;create desktop shortcut (nom fixe, sans version)
  CreateShortCut "$DESKTOP\${MUI_SHORTCUT_NAME}.lnk" "$INSTDIR\${MUI_FILE}.exe" "" "${SHORTCUT_ICON_EXE}" 0

;create start-menu items (dossier fixe)
  CreateDirectory "$SMPROGRAMS\${MUI_SHORTCUT_NAME}"
  CreateShortCut "$SMPROGRAMS\${MUI_SHORTCUT_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "${SHORTCUT_ICON_EXE}" 0
  CreateShortCut "$SMPROGRAMS\${MUI_SHORTCUT_NAME}\${MUI_SHORTCUT_NAME}.lnk" "$INSTDIR\${MUI_FILE}.exe" "" "${SHORTCUT_ICON_EXE}" 0

;write uninstall information to the registry (clé fixe)
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT_KEY}" "DisplayName" "${MUI_SHORTCUT_NAME} ${MUI_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT_KEY}" "DisplayVersion" "${MUI_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT_KEY}" "InstallLocation" "$INSTDIR"

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
  Delete "$DESKTOP\${MUI_SHORTCUT_NAME}.lnk"
  Delete "$SMPROGRAMS\${MUI_SHORTCUT_NAME}\*.*"
  RmDir  "$SMPROGRAMS\${MUI_SHORTCUT_NAME}"

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
  MessageBox MB_OK "You have successfully uninstalled ${MUI_SHORTCUT_NAME}."
FunctionEnd

;eof