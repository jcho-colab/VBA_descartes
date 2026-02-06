Attribute VB_Name = "mButtons"
Option Explicit 'Force explicit variable declaration

'################################################################
'#
'# Main button to execute everything in sequence
'#
'################################################################
Sub ExecuteAll()
    'Load settings object
    Dim oSettings As clsConfig: Set oSettings = New clsConfig
    
    'Execute processes
    If Not ImportXmlNOM(oSettings) Then Exit Sub    'Abort if import cancelled
    DataCleansingNOM oSettings
    If Not oSettings.Country = "US" Then            'Skip TXT if US
    If Not ImportXmlTXT(oSettings) Then Exit Sub    'Abort if import cancelled
    End If
    GenerateOutput oSettings
    
    'Output processing time
    Debug.Print "Total process time = " & oSettings.TotalTime & " sec"
    
    MsgBox "All operations are done!", vbInformation

End Sub

'################################################################
'#
'# Subprocess buttons
'#
'################################################################

Function ImportXmlNOM(Optional ByRef oSettings As clsConfig = Nothing) As Boolean
    'Apply configs in case of manual activation
    If oSettings Is Nothing Then Set oSettings = New clsConfig
    
    'Execute subprocess
    ImportXmlNOM = mSubs.ImportXML(oSettings, "NOM")
    
    If ImportXmlNOM Then
        'Set Last Run date
        shtMenu.Range("LastImportNOM").Value = Now
        shtMenu.Range("LastCleansingNOM").Value = Null
    End If
End Function

Sub DataCleansingNOM(Optional ByRef oSettings As clsConfig = Nothing)
    'Apply configs in case of manual activation
    If oSettings Is Nothing Then Set oSettings = New clsConfig
    
    'Execute subprocesses
    mSubs.DeleteEntries oSettings
    mSubs.ProcessHS oSettings
    mSubs.FlagHS oSettings
    mSubs.CompleteDescription oSettings
    
    'Set Last Run date
    shtMenu.Range("LastCleansingNOM").Value = Now
End Sub

Function ImportXmlTXT(Optional ByRef oSettings As clsConfig = Nothing) As Boolean
    'Apply configs in case of manual activation
    If oSettings Is Nothing Then Set oSettings = New clsConfig
    
    'Execute subprocess
    ImportXmlTXT = mSubs.ImportXML(oSettings, "TXT")
        
    'Set Last Run date
    If ImportXmlTXT Then shtMenu.Range("LastImportTXT").Value = Now
End Function

Sub GenerateOutput(Optional ByRef oSettings As clsConfig = Nothing)
    'Apply configs in case of manual activation
    If oSettings Is Nothing Then Set oSettings = New clsConfig
    
    'Execute subprocess
    mSubs.QueryOutput oSettings
    
    'Set Last Run date
    shtMenu.Range("LastGenOutput").Value = Now
End Sub

Sub ClearAll()
    'Ask user confirmation
    If MsgBox("Are you sure?", vbYesNo Or vbExclamation, _
        "Clear all data") = vbNo Then Exit Sub
    
    'Execute subprocess
    mSubs.EmptyTables
    
    'Reset Last Run dates
    shtMenu.Range("LastImportNOM").Value = Null
    shtMenu.Range("LastCleansingNOM").Value = Null
    shtMenu.Range("LastImportTXT").Value = Null
    shtMenu.Range("LastGenOutput").Value = Null
End Sub

'################################################################
'#
'# Export buttons
'#
'################################################################

Sub ExportHS()
    'Load settings object
    Dim oSettings As clsConfig: Set oSettings = New clsConfig
        
    'Export table in new Excel file
    ExportXLSX oSettings
End Sub
