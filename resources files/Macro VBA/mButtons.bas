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
    If Not ImportXmlDTR(oSettings) Then Exit Sub                   'Abort if import cancelled
    If Not mSubs.DataValidation(oSettings, "DTR") Then Exit Sub    'Spot check on data before continuing
    DataCleansingDTR oSettings
    If Not ImportXmlNOM(oSettings) Then Exit Sub                   'Abort if import cancelled
    If Not mSubs.DataValidation(oSettings, "NOM") Then Exit Sub    'Spot check on data before continuing
    DataCleansingNOM oSettings
    If Not ImportXmlTXT(oSettings) Then Exit Sub                   'Abort if import cancelled
    GenerateOutput oSettings
    
    'Output processing time
    Debug.Print "Total process time = " & oSettings.TotalTime & " sec"
    
    MsgBox "All operations are done!", vbInformation

End Sub

'################################################################
'#
'# Individual buttons / subprocesses
'#
'################################################################

Function ImportXmlDTR(Optional ByRef oSettings As clsConfig = Nothing) As Boolean
    'Apply configs in case of manual activation
    If oSettings Is Nothing Then Set oSettings = New clsConfig
    
    'Execute subprocess
    ImportXmlDTR = mSubs.ImportXML(oSettings, "DTR")
    
    If ImportXmlDTR Then
        'Set Last Run date
        shtMenu.Range("LastImportDTR").Value = Now
        shtMenu.Range("LastCleansingDTR").Value = Null
    End If
End Function

Sub DataCleansingDTR(Optional ByRef oSettings As clsConfig = Nothing)
    'Apply configs and validation in case of manual activation
    If oSettings Is Nothing Then
        Set oSettings = New clsConfig
        If Not mSubs.DataValidation(oSettings, "DTR") Then Exit Sub
    End If
    
    'Execute subprocesses
    mSubs.DeleteEntries oSettings, "DTR", "concat_cg_drt"
    mSubs.DeleteEntries oSettings, "DTR", "hs"
    mSubs.ProcessHS oSettings, "DTR"
    mSubs.FlagHS oSettings, "DTR"
    
    'Set Last Run date
    shtMenu.Range("LastCleansingDTR").Value = Now
End Sub

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
    If oSettings Is Nothing Then
        Set oSettings = New clsConfig
        If Not mSubs.DataValidation(oSettings, "NOM") Then Exit Sub
    End If
    
    'Execute subprocesses
    mSubs.DeleteEntries oSettings, "NOM", "hs"
    mSubs.ProcessHS oSettings, "NOM"
    mSubs.FlagHS oSettings, "NOM"
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
    mSubs.QueryOutput oSettings, "ZD14"
    Select Case oSettings.Country
        Case "CA"
            mSubs.QueryOutput oSettings, "CAPDR"
            mSubs.QueryOutput oSettings, "ZZDE"
        Case "MX"
            mSubs.QueryOutput oSettings, "MX6Digits"
        Case "US"
            mSubs.QueryOutput oSettings, "ZZDF"
    End Select
    
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
    shtMenu.Range("LastImportDTR").Value = Null
    shtMenu.Range("LastCleansingDTR").Value = Null
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

Sub ExportZD14()
    'Load settings object
    Dim oSettings As clsConfig: Set oSettings = New clsConfig
    
    'Special process for EU
    If oSettings.Country = "EU" Then _
        If MsgBox("Export CSV for all countries?", vbYesNo Or vbQuestion) = vbNo Then _
            oSettings.CountryList = Array(oSettings.TableZD14.ListColumns("Country").DataBodyRange(1).Value)
    
    Dim vCountry As Variant
    For Each vCountry In oSettings.CountryList
        'Change country value in table
        oSettings.TableZD14.ListColumns("Country").DataBodyRange.Value = vCountry
        
        'Export table in multiple CSV files
        ExportCSV oSettings, "ZD14"
    Next vCountry
End Sub

Sub ExportCAPDR()
    'Load settings object
    Dim oSettings As clsConfig: Set oSettings = New clsConfig
    
    'Export table in multiple CSV files
    mSubs.ExportCSV oSettings, "CAPDR"
End Sub

Sub ExportMX6Digits()
    'Load settings object
    Dim oSettings As clsConfig: Set oSettings = New clsConfig
    
    'Export table in multiple CSV files
    mSubs.ExportCSV oSettings, "MX6Digits"
End Sub

Sub ExportZZDE()
    'Load settings object
    Dim oSettings As clsConfig: Set oSettings = New clsConfig
    
    'Export table in multiple CSV files
    mSubs.ExportCSV oSettings, "ZZDE"
End Sub

Sub ExportZZDF()
    'Load settings object
    Dim oSettings As clsConfig: Set oSettings = New clsConfig
    
    'Export table in multiple CSV files
    mSubs.ExportCSV oSettings, "ZZDF"
End Sub

Sub ExportZD14Test()
    'Load settings object
    Dim oSettings As clsConfig: Set oSettings = New clsConfig
    
    'Export table in multiple CSV files
    mSubs.ExportCSV oSettings, "ZD14Test"
End Sub


