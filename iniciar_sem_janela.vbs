Option Explicit

Dim WshShell, FSO, processEnv, pastaProjeto, caminhoApp, caminhoVerificador
Dim caminhoLog, iniciou, comandoPython, comandoPythonw, codigoSaida, pronto
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
pronto = False

' O VBS nao instala dependencias. Testa primeiro para falhar rapido e orientar o uso do .bat.
comandoPython = "py -3"
codigoSaida = ExecutarOculto(comandoPython & " -c ""import flask, watchdog, openpyxl""")
If codigoSaida <> 0 Then
    comandoPython = "python"
    codigoSaida = ExecutarOculto(comandoPython & " -c ""import flask, watchdog, openpyxl""")
End If
If codigoSaida <> 0 Then
    MsgBox "As dependencias do Sistema Terra nao estao instaladas para este Python. Execute primeiro iniciar_sistema.bat para instalar e configurar o sistema.", vbExclamation, "Sistema Terra - Configuracao inicial"
    WScript.Quit 1
End If

If comandoPython = "py -3" Then
    comandoPythonw = "pyw -3"
Else
    comandoPythonw = "pythonw"
End If

' Inicia o servidor sem manter uma janela de terminal aberta.
On Error Resume Next
WshShell.Run comandoPythonw & " """ & caminhoApp & """", 0, False
If Err.Number = 0 Then iniciou = True
Err.Clear

' Algumas instalacoes tem pythonw.exe mas nao o comando pyw.
If Not iniciou And comandoPythonw <> "pythonw" Then
    comandoPythonw = "pythonw"
    WshShell.Run comandoPythonw & " """ & caminhoApp & """", 0, False
    If Err.Number = 0 Then iniciou = True
    Err.Clear
End If
On Error GoTo 0

If Not iniciou Then
    MsgBox "Nao encontrei pyw nem pythonw nesta maquina. Instale Python 3 para Windows e execute iniciar_sistema.bat para configurar as dependencias.", vbExclamation, "Sistema Terra - Python ausente"
    WScript.Quit 1
End If

' Aguarda a resposta do Flask; nao abre uma pagina 127.0.0.1 antes de o servidor estar pronto.
codigoSaida = ExecutarOculto(comandoPython & " """ & caminhoVerificador & """")
If codigoSaida = 0 Then pronto = True

If Not pronto Then
    MsgBox "O processo do Sistema Terra foi iniciado, mas o servidor nao respondeu em http://127.0.0.1:5000/healthz. Verifique a pasta do projeto e o arquivo sistema_terra.log. Se o erro continuar, envie esse log para suporte.", vbExclamation, "Sistema Terra - Falha ao iniciar"
    If FSO.FileExists(caminhoLog) Then WshShell.Run "notepad.exe """ & caminhoLog & """", 1, False
    WScript.Quit 1
End If

WshShell.Run "http://127.0.0.1:5000", 1, False

Function ExecutarOculto(comando)
    On Error Resume Next
    ExecutarOculto = WshShell.Run(comando, 0, True)
    If Err.Number <> 0 Then ExecutarOculto = -1
    Err.Clear
    On Error GoTo 0
End Function
