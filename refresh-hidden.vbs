' ============================================================================
' City Buy List - lanceur silencieux du refresh de donnees.
'
' POURQUOI CE FICHIER EXISTE :
' Le planificateur de taches Windows lancait refresh-data.bat directement, ce qui
' ouvrait une fenetre de console VISIBLE en pleine journee. Comme refresh-data.bat
' redirige toute sa sortie vers refresh.log, cette fenetre restait NOIRE ET VIDE
' pendant ~1h39. Resultat previsible : elle se faisait fermer a la main (reaction
' saine face a une fenetre noire inexpliquee), ce qui tuait le refresh en cours.
' Constate les 14/07 et 15/07/2026 : code de sortie 0xC000013A (CTRL+C), donnees
' figees a J-1.
'
' CE QUE CA FAIT :
' Lance refresh-data.bat dans le MEME dossier que ce script, en fenetre CACHEE
' (parametre 0), attend la fin (True), et renvoie son code de sortie au
' planificateur pour que LastTaskResult reste fiable (0 = succes).
'
' USAGE :
' Reserve au planificateur de taches. Pour un refresh manuel, double-cliquer
' refresh-data.bat : la fenetre visible est normale et voulue dans ce cas.
' ============================================================================
Option Explicit
Dim sh, fso, here, bat, rc

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' meme dossier que ce script (equivalent VBS du %~dp0 de refresh-data.bat)
here = fso.GetParentFolderName(WScript.ScriptFullName)
bat = fso.BuildPath(here, "refresh-data.bat")

If Not fso.FileExists(bat) Then
  ' code distinctif : le planificateur montrera 2 au lieu d'un echec muet
  WScript.Quit 2
End If

rc = sh.Run("""" & bat & """", 0, True)
WScript.Quit rc
