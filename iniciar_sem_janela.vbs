Option Explicit

Dim WshShell, FSO, processEnv, pastaProjeto, caminhoApp, caminhoVerificador
Dim caminhoLog, iniciou, comandoPython, codigoSaida, pronto
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
Set processEnv = WshShell.Environment("Process")
processEnv("PORT") = "5000"

pastaProjeto = FSO.GetParentFolderName(WScript.ScriptFullName)
caminhoApp = FSO.BuildPath(pastaProjeto, "app.py")
caminhoVerificador = FSO.BuildPath(pastaProjeto, "wait_for_server.py")
caminhoLog = FSO.BuildPath(pastaProjeto, "sistema_terra.log")
WshShell.CurrentDirectory = pastaProjeto
iniciou = False
comandoPython = ""

' O Launcher pyw inicia o Python sem console, mesmo quando pythonw.exe nao esta no PATH.
On Error Resume Next
WshShell.Run "pyw -3 """ & caminhoApp & """", 0, False
If Err.Number = 0 Then
    iniciou = True
    comandoPython = "py -3"
End If
Err.Clear

' Alternativa para instalacoes que expoem pythonw.exe diretamente.
If Not iniciou Then
    WshShell.Run "pythonw """ & caminhoApp & """", 0, False
    If Err.Number = 0 Then
        iniciou = True
        comandoPython = "python"
    End If
    Err.Clear
End If
On Error GoTo 0

If Not iniciou Then
    MsgBox "Nao encontrei pyw nem pythonw nesta maquina. Instale Python 3 para Windows, incluindo o Python Launcher. Depois execute iniciar_sistema.bat para configurar as dependencias e tente novamente.", vbExclamation, "Sistema Terra - Python ausente"
    WScript.Quit 1
End If

' Aguarda a resposta do Flask; nao abre uma pagina 127.0.0.1 antes de o servidor estar pronto.
On Error Resume Next
codigoSaida = WshShell.Run(comandoPython & " """ & caminhoVerificador & """", 0, True)
If Err.Number = 0 And codigoSaida = 0 Then pronto = True
Err.Clear
On Error GoTo 0

If Not pronto Then
    MsgBox "O processo do Sistema Terra foi iniciado, mas o servidor nao respondeu em http://127.0.0.1:5000/healthz. Verifique a pasta do projeto e o arquivo sistema_terra.log. Se o erro continuar, envie esse log para suporte.", vbExclamation, "Sistema Terra - Falha ao iniciar"
    If FSO.FileExists(caminhoLog) Then WshShell.Run "notepad.exe """ & caminhoLog & """", 1, False
    WScript.Quit 1
End If

WshShell.Run "http://127.0.0.1:5000", 1, False
