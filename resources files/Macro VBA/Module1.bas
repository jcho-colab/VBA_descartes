Attribute VB_Name = "Module1"
Sub ExportAllCode()
    Dim vbComp As Object ' Use Object instead of VBComponent
    Dim filePath As String
   
    ' Set export folder
    filePath = "D:\MacroExport\" & ThisWorkbook.Name & "\"
   
    ' Create folder if it doesn't exist
    If Dir(filePath, vbDirectory) = "" Then
        MkDir filePath
    End If
   
    ' Export all components
    For Each vbComp In ThisWorkbook.VBProject.VBComponents
        Select Case vbComp.Type
            Case 1, 2 ' vbext_ct_StdModule = 1, vbext_ct_ClassModule = 2
                vbComp.Export filePath & vbComp.Name & ".bas"
            Case 3 ' vbext_ct_MSForm = 3
                vbComp.Export filePath & vbComp.Name & ".frm"
            ' Skip vbext_ct_Document components (e.g., ThisWorkbook, Sheet1, etc.)
        End Select
    Next vbComp
   
    MsgBox "Code exported to: " & filePath
End Sub
