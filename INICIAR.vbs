' ============================================================
'  Lançador do Sistema de Cartão Ponto (pasta portátil)
'  Inicia o servidor com o Python embutido, sem janela preta,
'  e abre o navegador automaticamente.
' ============================================================
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

' Pasta onde este .vbs está
base = fso.GetParentFolderName(WScript.ScriptFullName)

pythonExe = base & "\runtime\python.exe"
mainPy    = base & "\app\main.py"

If Not fso.FileExists(pythonExe) Then
    MsgBox "Python embutido nao encontrado em:" & vbCrLf & pythonExe & vbCrLf & _
           "A pasta pode estar incompleta. Reextraia o ZIP completo.", 16, "Cartao Ponto"
    WScript.Quit
End If

' Inicia o servidor oculto (0 = janela invisivel). main.py abre o navegador.
sh.CurrentDirectory = base & "\app"
sh.Run """" & pythonExe & """ """ & mainPy & """", 0, False
