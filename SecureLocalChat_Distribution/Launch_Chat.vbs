' SecureLocal Chat Silent Launcher
Set WshShell = CreateObject("WScript.Shell")

' Get the directory where this script is located
strPath = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, ""))

' Launch the executable silently
WshShell.Run Chr(34) & strPath & "SecureLocalChat.exe" & Chr(34), 0, False

' Wait for app to start
WScript.Sleep 3000

' Open browser
WshShell.Run "http://localhost:5000"
