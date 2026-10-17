Option Explicit

Dim WshShell, FSO, pastaProjeto, caminhoApp, iniciou
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

pastaProjeto = FSO.GetParentFolderName(WScript.ScriptFullName)
caminhoApp = FSO.BuildPath(pastaProjeto, "app.py")
WshShell.CurrentDirectory = pastaProjeto
iniciou = False

' O Launcher pyw inicia o Python sem console, mesmo quando pythonw.exe nao esta no PATH.
On Error Resume Next
WshShell.Run "pyw -3 """ & caminhoApp & """", 0, False
If Err.Number = 0 Then iniciou = True
Err.Clear

' Alternativa para instalacoes que expoem pythonw.exe diretamente.
If Not iniciou Then
    WshShell.Run "pythonw """ & caminhoApp & """", 0, False
    If Err.Number = 0 Then iniciou = True
    Err.Clear
End If
On Error GoTo 0

If Not iniciou Then
    MsgBox "Nao encontrei pyw nem pythonw nesta maquina. Instale Python 3 para Windows, incluindo o Python Launcher. Depois execute iniciar_sistema.bat para configurar as dependencias e tente novamente.", vbExclamation, "Sistema Terra - Python ausente"
    WScript.Quit 1
End If

WScript.Sleep 2000
WshShell.Run "http://127.0.0.1:5000", 1, False
