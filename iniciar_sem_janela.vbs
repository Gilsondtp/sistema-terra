Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath
WshShell.Run "pythonw app.py", 0, False
WScript.Sleep 1500
WshShell.Run "http://localhost:5000", 1, False
