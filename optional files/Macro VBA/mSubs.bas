Attribute VB_Name = "mSubs"
Option Explicit 'Force explicit variable declaration

Function ImportXML(ByVal oSettings As clsConfig, _
    ByVal sDataType As String) As Boolean
'################################################################
'#
'# Import XML files with file dialog and progress bar update.
'# Check if data exists, posssibility to clear for full data load
'# or to keep actual and append update only.
'#
'# Returns False if file selection was cancelled or if total
'# number of entries exceeds Excel's limitation
'#
'################################################################
    'Define values based on the data type
    Dim loTable As ListObject, loDefinition As ListObject, loFileList As ListObject
    Dim sFileName As String, sNode As String, sMappingXML As String
    Select Case sDataType
        Case "DTR"
            Set loTable = oSettings.TableDTR
            Set loDefinition = oSettings.DefinitionDTR
            Set loFileList = oSettings.FileListDTR
            sFileName = oSettings.FileNameDTR
            sNode = "//duty_rate/body/duty_rate_entity"
            sMappingXML = oSettings.MappingDTR
        Case "NOM"
            Set loTable = oSettings.TableNOM
            Set loDefinition = oSettings.DefinitionNOM
            Set loFileList = oSettings.FileListNOM
            sFileName = oSettings.FileNameNOM
            sNode = "//legal_numbering_exchange/body/number_data"
            sMappingXML = oSettings.MappingNOM
        Case "TXT"
            Set loTable = oSettings.TableTXT
            Set loDefinition = oSettings.DefinitionTXT
            Set loFileList = oSettings.FileListTXT
            sFileName = oSettings.FileNameTXT
            sNode = "//legal_numbering_exchange/body/texts"
            sMappingXML = oSettings.MappingTXT
    End Select
    
    'If table not empty
    If Not loTable.DataBodyRange Is Nothing Then
        'Message Box to ask the user if we clear the data before importing xml files
        If MsgBox("Do you want to overwrite the actual data?", vbYesNo Or vbQuestion, "Overwrite?") = vbYes Then
            'Clear table
            ResetFilters loTable: loTable.DataBodyRange.Delete
            'Clear definition associated table
            If Not loDefinition.DataBodyRange Is Nothing Then _
                ResetFilters loDefinition: loDefinition.DataBodyRange.Delete
            'Clear file list table
            If Not loFileList.DataBodyRange Is Nothing Then _
                ResetFilters loFileList: loFileList.DataBodyRange.Delete
        End If
    End If
    
    'Define a file dialog for file selection with specific filters to load only appropriate files
    Dim fd As Office.FileDialog: Set fd = Application.FileDialog(msoFileDialogFilePicker)
    With fd
        .Filters.Clear
        .Filters.Add "XML File", "*.xml", 1
        .Title = "Select " & loTable.Name & " XML file(s)"
        .AllowMultiSelect = True
        .InitialFileName = Application.ThisWorkbook.Path & Application.PathSeparator & _
            "XML" & Application.PathSeparator & sFileName
        
        'Show file dialog, if file selection is cancelled, abort process
        ImportXML = .Show: If ImportXML = False Then Exit Function
    End With
    
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Initialise progress bar
    LaunchProgressBar ""
    
    'Initialize XML object
    Dim oXmlDoc As Object: Set oXmlDoc = CreateObject("Microsoft.XMLDOM")
    oXmlDoc.async = False: oXmlDoc.validateOnParse = False
    
    'Loop through selected files
    Dim iFile As Integer
    For iFile = 1 To fd.SelectedItems.Count
        'Update progress bar
        UpdateProgressBar "Processing file " & iFile & " of " & fd.SelectedItems.Count, _
            iFile, fd.SelectedItems.Count, 1
        
        'Load the XML data
        oXmlDoc.Load (fd.SelectedItems(iFile))
        Debug.Print "File " & iFile & " node count = " & oXmlDoc.SelectNodes(sNode).Length
        
        'If Excel line limitation will not be reached
        If Not loTable.ListRows.Count + oXmlDoc.SelectNodes(sNode).Length > 1048570 Then
            'Import the data from the loaded XML to the table
            ThisWorkbook.XmlMaps(sMappingXML).ImportXML oXmlDoc.XML, False

            With loFileList
                'Add row to file list table
                .ListRows.Add
                'Log file name in the new row
                Dim sPath() As String: sPath = Split(oXmlDoc.Url, "/")
                .ListColumns(sDataType & " File List").DataBodyRange(.ListRows.Count).Value = sPath(UBound(sPath))
            End With
        Else:
            'Build the message
            Dim sMessage As String: sMessage = "Excel line limit reached. Cleanse the actual data, " & _
                "then retry the import process for the following files:" & vbCrLf

            Dim iMissingFile As Integer ', sPath() As String
            For iMissingFile = iFile To fd.SelectedItems.Count
                sPath = Split(fd.SelectedItems(iMissingFile), Application.PathSeparator)
                sMessage = sMessage & vbCrLf & sPath(UBound(sPath))
            Next iMissingFile

            'Inform user and abort process
            MsgBox sMessage, vbCritical, "Exceeding Excel capacity : too many lines"
            ImportXML = False: Exit For
        End If
    Next iFile
    
    'Dispose of XML object
    Set oXmlDoc = Nothing

    'Remove duplicates from the definition associated table
    CleanseDefinitions loDefinition
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Import time = " & tEnd & " sec"
        
End Function

Function DataValidation(ByVal oSettings As clsConfig, _
    ByVal sDataType As String) As Boolean
'################################################################
'#
'# Execute validation processes in sequence
'#
'################################################################
    Select Case sDataType
        Case "DTR"
            'Check if rates are valid
            DataValidation = RateValidation(oSettings)
        Case "NOM"
            'Skip to configuration validation
            DataValidation = True
    End Select
    
    'If rates are valid, validate configurations
    If DataValidation Then DataValidation = ConfigValidation(oSettings, sDataType)
    
End Function

Sub DeleteEntries(ByVal oSettings As clsConfig, _
    ByVal sDataType As String, ByVal sColumnName As String)
'################################################################
'#
'# Delete the unnecessary entries with a progress bar update
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Define values based on the data type
    Dim loTable As ListObject
    Select Case sDataType
        Case "DTR"
            Set loTable = oSettings.TableDTR
        Case "NOM"
            Set loTable = oSettings.TableNOM
    End Select
    
    'Initialise progress bar
    LaunchProgressBar "Fetching " & sColumnName & " details"
    
    'Reset filters
    ResetFilters loTable
    
    'Define criterias based on the column name
    Dim vCriterias As Variant
    Select Case sColumnName
        Case "hs"
            vCriterias = ValidateList( _
                rRange:=loTable.ListColumns(sColumnName).DataBodyRange, _
                vInitialList:=oSettings.ChapterList)
        Case "concat_cg_drt"
            vCriterias = GetOppositeList( _
                rRange:=loTable.ListColumns(sColumnName).DataBodyRange, _
                vInitialList:=oSettings.ActiveCountryGroupList)
    End Select
    
    'Skip if no criteria to remove
    If Not IsEmpty(vCriterias) Then
        'Update progress bar
        UpdateProgressBar "Sorting by " & sColumnName
        
        'Sort by criteria for faster deletion, fewer areas
        SortColumn loTable, sColumnName
        
        'Loop through criterias
        Dim iCriteria As Integer
        For iCriteria = LBound(vCriterias) To UBound(vCriterias)
            'If hs, adjust the criteria output
            If sColumnName = "hs" Then vCriterias(iCriteria) = "=" & vCriterias(iCriteria) & "*"
            
            'Update progress bar
            UpdateProgressBar "Deleting " & sColumnName & " " & vCriterias(iCriteria) & " entries", _
                iCriteria, UBound(vCriterias), 5
            
            'Set the filter for the unwanted values
            loTable.Range.AutoFilter _
                Field:=loTable.ListColumns(sColumnName).Index, _
                Criteria1:=vCriterias(iCriteria)
                
            'Delete the unwanted values
            loTable.DataBodyRange.SpecialCells(xlCellTypeVisible).EntireRow.Delete
        Next iCriteria
        
        'Reset filters
        loTable.AutoFilter.ShowAllData
    End If
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Delete " & sColumnName & " time = " & tEnd & " sec"
    
End Sub

Sub ProcessHS(ByVal oSettings As clsConfig, _
    ByVal sDataType As String)
'################################################################
'#
'# Remove double leading zeros on HS with a progress bar update
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Define values based on the data type
    Dim loTable As ListObject
    Select Case sDataType
        Case "DTR"
            Set loTable = oSettings.TableDTR
        Case "NOM"
            Set loTable = oSettings.TableNOM
    End Select
    
    'Initialise progress bar
    LaunchProgressBar "Fetching HS details"
    
    'Reset filters
    ResetFilters loTable
    
    'Skip if no double leading zeros
    If Not IsEmpty(ValidateList( _
        rRange:=loTable.ListColumns("hs").DataBodyRange, _
        vInitialList:=Array("00"))) Then
        
        'Update progress bar
        UpdateProgressBar "Sorting and filtering HS"
        
        'Sort by HS for faster process, fewer areas
        SortColumn loTable, "hs"
        
        'Filter HS with double leading zeros only
        loTable.Range.AutoFilter _
            Field:=loTable.ListColumns("hs").Index, _
            Criteria1:="=00*"
        
        'Loop through all visible rows in table
        With loTable.ListColumns("hs").DataBodyRange.SpecialCells(xlCellTypeVisible)
            Dim lRow As Long
            For lRow = 1 To .Rows.Count
                'Update progress bar once every 500 iterations
                If lRow Mod 500 = 0 _
                Then UpdateProgressBar "Processing 00* HS, line " & lRow & " of " & .Rows.Count, _
                    lRow, .Rows.Count

                'Remove double leading zeros
                .Cells(lRow).Value = Right(.Cells(lRow).Value, Len(.Cells(lRow).Value) - 2)
            Next lRow
        End With
        
        'Reset filters
        loTable.AutoFilter.ShowAllData
    End If
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Process HS time = " & tEnd & " sec"
    
End Sub

Sub FlagHS(ByVal oSettings As clsConfig, _
    ByVal sDataType As String)
'################################################################
'#
'# Flag HS values to query valid last update only, with
'# progress bar update
'#
'# Flags : 01-active, 02-invalid, 03-duplicate
'#
'# DTR key : hs and country_group
'# NOM key : hs and version_number
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Define values based on the data type
    Dim loTable As ListObject, sKey2 As String
    Select Case sDataType
        Case "DTR"
            Set loTable = oSettings.TableDTR
            sKey2 = "country_group"
        Case "NOM"
            Set loTable = oSettings.TableNOM
            sKey2 = "version_number"
    End Select
    
    'Initialise progress bar
    LaunchProgressBar "Sorting data to flag HS"
    
    'Reset filters
    ResetFilters loTable
    
    'Sort data by priority
    With loTable.Sort
        'To avoid multiple areas when filtering for each elements
        .SortFields.Add _
            Key:=.Parent.ListColumns(sKey2).Range, _
            SortOn:=xlSortOnValues, _
            Order:=xlAscending, _
            DataOption:=xlSortNormal
        'Put all similar HS together
        .SortFields.Add _
            Key:=.Parent.ListColumns("hs").Range, _
            SortOn:=xlSortOnValues, _
            Order:=xlAscending, _
            DataOption:=xlSortNormal
        'From updates (higher / later) to initial load (lower / earlier)
        .SortFields.Add _
            Key:=.Parent.ListColumns("version_date").Range, _
            SortOn:=xlSortOnValues, _
            Order:=xlDescending, _
            DataOption:=xlSortNormal
        'From updates (higher / later) to initial load (lower / earlier)
        .SortFields.Add _
            Key:=.Parent.ListColumns("valid_from").Range, _
            SortOn:=xlSortOnValues, _
            Order:=xlDescending, _
            DataOption:=xlSortNormal
        'From specific dates (lower / earlier) to end of times (higher / later)
        .SortFields.Add _
            Key:=.Parent.ListColumns("valid_to").Range, _
            SortOn:=xlSortOnValues, _
            Order:=xlAscending, _
            DataOption:=xlSortNormal
        If sDataType = "DTR" Then
            'From higher rate to lower rate for adValoremRate_percentage
            .SortFields.Add _
                Key:=.Parent.ListColumns("adValoremRate_percentage").Range, _
                SortOn:=xlSortOnValues, _
                Order:=xlDescending, _
                DataOption:=xlSortNormal
            'From higher rate to lower rate for specificRate_ratePerUOM
            .SortFields.Add _
                Key:=.Parent.ListColumns("specificRate_ratePerUOM").Range, _
                SortOn:=xlSortOnValues, _
                Order:=xlDescending, _
                DataOption:=xlSortNormal
            'From higher rate to lower rate for compoundRate_percentage
            .SortFields.Add _
                Key:=.Parent.ListColumns("compoundRate_percentage").Range, _
                SortOn:=xlSortOnValues, _
                Order:=xlDescending, _
                DataOption:=xlSortNormal
        End If
        .Header = xlYes
        .MatchCase = False
        .Orientation = xlTopToBottom
        .SortMethod = xlPinYin
        .Apply
        .SortFields.Clear
    End With
    
    'Get item list from the second key column
    Dim vItems As Variant: vItems = GetOppositeList(loTable.ListColumns(sKey2).DataBodyRange)
    
    'Loop through all items
    Dim iItem As Integer
    For iItem = LBound(vItems) To UBound(vItems)
        'Update progress bar
        UpdateProgressBar "Flagging " & sKey2 & " " & vItems(iItem) & " HS", _
                iItem, UBound(vItems), 1
        
        'Set the filter to analyse each item individually
        loTable.Range.AutoFilter _
            Field:=loTable.ListColumns(sKey2).Index, _
            Criteria1:=vItems(iItem)
        
        'Initialize dictionary
        Dim oHSDict As Object: Set oHSDict = CreateObject("Scripting.Dictionary")
        
        'Loop through all visible cells of column
        Dim rCell As Range
        For Each rCell In loTable.ListColumns("hs").DataBodyRange.SpecialCells(xlCellTypeVisible).Cells
            'rCell relative index
            Dim lIndex As Long: lIndex = rCell.Row - rCell.ListObject.Range.Row
            
            'If not in dictionary, add it and check date
            If Not oHSDict.Exists(rCell.Value) Then
                oHSDict.Add rCell.Value, Nothing
                'If valid_to date is within the processed year, flag as active
                If Left(loTable.ListColumns("valid_to").DataBodyRange(lIndex).Value, 4) >= oSettings.Year Then
                    loTable.ListColumns("hs_flag").DataBodyRange(lIndex).Value = "01-active"
                'If valid_to date is earlier then start of processed year, flag as invalid
                Else: loTable.ListColumns("hs_flag").DataBodyRange(lIndex).Value = "02-invalid"
                End If
            'If in dictionary, flag as duplicate
            Else: loTable.ListColumns("hs_flag").DataBodyRange(lIndex).Value = "03-duplicate"
            End If
        Next rCell
    
        'Dispose of dictionary
        Set oHSDict = Nothing
    Next iItem

    'Reset filters
    loTable.AutoFilter.ShowAllData
    
    'Update progress bar
    UpdateProgressBar "Sorting by HS"
    
    'Sort data by HS
    SortColumn loTable, "hs"
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Flag HS time = " & tEnd & " sec"
    
End Sub

Sub CompleteDescription(ByVal oSettings As clsConfig)
'################################################################
'#
'# Builds the full description by adding the all parent's
'# description in the hierarchy
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Initialise progress bar
    LaunchProgressBar "Sorting data to format descriptions"
    
    'Reset filters
    ResetFilters oSettings.TableNOM
    
    'Put duplicate and invalid entries at the bottom of the list
    SortColumn oSettings.TableNOM, "hs_flag"
    
    'Initialize dictionary
    Dim oDescriptionDict As Object: Set oDescriptionDict = CreateObject("Scripting.Dictionary")
    
    With oSettings.TableNOM
        'Loop though every row in the table
        Dim lRow As Long
        For lRow = 1 To .ListRows.Count
            'Update progress bar once every 1000 iterations
            If lRow Mod 1000 = 0 _
            Then UpdateProgressBar "Formatting description " & lRow & " of " & .ListRows.Count, _
                lRow, .ListRows.Count
            
            'Build full description from parents and replace ; by . for CSV purposes
            If Not .ListColumns("level_id").DataBodyRange(lRow).Value = 10 Then
                .ListColumns("full_description").DataBodyRange(lRow).Value = _
                    oDescriptionDict.Item(.ListColumns("parent_id").DataBodyRange(lRow).Value) & "---" & _
                    ReplaceChars(.ListColumns("official_description").DataBodyRange(lRow).Value)
            'If level 10, copy official description in full description and replace ; by . for CSV purposes
            Else: .ListColumns("full_description").DataBodyRange(lRow).Value = _
                    ReplaceChars(.ListColumns("official_description").DataBodyRange(lRow).Value)
            End If
            
            'Build the dictionary, exclude level 50 because never reused
            If Not .ListColumns("level_id").DataBodyRange(lRow).Value = 50 Then
                'If not in dictionary, add it
                If Not oDescriptionDict.Exists(.ListColumns("id").DataBodyRange(lRow).Value) Then
                    oDescriptionDict.Add .ListColumns("id").DataBodyRange(lRow).Value, _
                        .ListColumns("full_description").DataBodyRange(lRow).Value
                'If in dictionary, change the item value (full_description)
                Else: oDescriptionDict.Item(.ListColumns("id").DataBodyRange(lRow).Value) = _
                        .ListColumns("full_description").DataBodyRange(lRow).Value
                End If
            End If
        Next lRow
    End With
    
    'Dispose of dictionary
    Set oDescriptionDict = Nothing
    
    'Update progress bar
    UpdateProgressBar "Sorting by HS"
    
    'Sort data by HS
    SortColumn oSettings.TableNOM, "hs"
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Description time = " & tEnd & " sec"
    
End Sub

Sub QueryOutput(ByVal oSettings As clsConfig, _
    ByVal sDataType As String)
'################################################################
'#
'# Refresh query table and adjust values with progress bar update
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Define values based on the data type
    Dim loTable As ListObject
    Select Case sDataType
        Case "ZD14"
            Set loTable = oSettings.TableZD14
        Case "CAPDR"
            Set loTable = oSettings.TableCAPDR
        Case "MX6Digits"
            Set loTable = oSettings.TableMX6Digits
        Case "ZZDE"
            Set loTable = oSettings.TableZZDE
        Case "ZZDF"
            Set loTable = oSettings.TableZZDF
    End Select
    
    'Initialise progress bar
    mSubs.LaunchProgressBar "Updating " & sDataType & " query table"
    
    'Refresh query table
    loTable.QueryTable.Refresh BackgroundQuery:=False
    
        'Special process for ZZDF
    If sDataType = "ZZDF" Then
        'Update progress bar
        mSubs.UpdateProgressBar "Replacing 'T' with 'TO' in ZZDF"
        
        'Replace 'T' with 'TO' in all columns of ZZDF
        Dim rCell As Range
        For Each rCell In loTable.DataBodyRange
            If rCell.Value = "T" Then
                rCell.Value = "TO"
            End If
        Next rCell
    End If
    
    'Special process for ZD14
    If sDataType = "ZD14" Then
        'Update progress bar
        mSubs.UpdateProgressBar "Replacing units of measure"
        
        'Replace UOM from config table
        
        For Each rCell In loTable.ListColumns("Unit of measure").DataBodyRange
          
            ' Replace UOM using the dictionary
            If oSettings.UOMDict.Exists(rCell.Value) Then _
                rCell.Value = oSettings.UOMDict(rCell.Value)
            
            ' Special replacement for country 'US'
            If oSettings.Country = "US" And rCell.Value = "T" Then
                rCell.Value = "TO"

            End If

        Next rCell
        
        'Special process for Brazil
        If oSettings.Country = "BR" Then _
            loTable.ListColumns("Rate amount").DataBodyRange.Value = Null
    End If
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print sDataType & " update time = " & tEnd & " sec"
End Sub

Sub ExportCSV(ByVal oSettings As clsConfig, _
    ByVal sDataType As String)
'################################################################
'#
'# Export the full table in multiple CSV files of maximum size
'#
'################################################################
    'Define values based on the data type
    Dim sCountry As String, loTable As ListObject
    Select Case sDataType
        Case "ZD14"
            sCountry = oSettings.TableZD14.ListColumns("Country").DataBodyRange(1).Value
            Set loTable = oSettings.TableZD14
        Case "CAPDR"
            sCountry = oSettings.Country
            Set loTable = oSettings.TableCAPDR
        Case "MX6Digits"
            sCountry = oSettings.Country
            Set loTable = oSettings.TableMX6Digits
        Case "ZZDE"
            sCountry = oSettings.Country
            Set loTable = oSettings.TableZZDE
        Case "ZZDF"
            sCountry = oSettings.Country
            Set loTable = oSettings.TableZZDF
        Case "ZD14Test"
            sCountry = oSettings.TableZD14Test.ListColumns("Country").DataBodyRange(1).Value
            Set loTable = oSettings.TableZD14Test
    End Select
    
    'Find unique file name
    Dim sFileName As String: sFileName = ThisWorkbook.Path & Application.PathSeparator & _
        "CSV" & Application.PathSeparator & sCountry & " UPLOAD " & loTable.Name & " V"
    Dim iVersion As Integer: iVersion = 1
    Do While Dir(sFileName & iVersion & "-1.csv") <> ""
        iVersion = iVersion + 1
    Loop
    
    'Set final file name version
    sFileName = sFileName & iVersion
    
    'While end of table not reached
    Dim lRow As Long: lRow = 1
    Dim iFile As Integer: iFile = 1
    Do While lRow <= loTable.DataBodyRange.Rows.Count
        'Create a new workbook
        Dim wbCSV As Workbook: Set wbCSV = Workbooks.Add
        
        'Copy-Paste header row
        loTable.HeaderRowRange.Copy wbCSV.Sheets(1).Cells(1, 1)
        
        'Set end of content range to copy
        Dim lEndRow As Long: lEndRow = lRow + oSettings.MaxCSV - 1
        'If range is bigger then table, set range to end of table
        If lEndRow >= loTable.DataBodyRange.Rows.Count Then _
            lEndRow = loTable.DataBodyRange.Rows.Count
        
        'Copy-Paste content rows below the header
        Range(loTable.ListRows(lRow).Range, loTable.ListRows(lEndRow).Range).Copy _
            wbCSV.Sheets(1).Cells(2, 1)
        
        'Don't ask and overwrite output if exist
        Application.DisplayAlerts = False
        
        'Save CSV file
        wbCSV.SaveAs Filename:=sFileName & "-" & iFile & ".csv", _
            FileFormat:=xlCSVUTF8, CreateBackup:=False, Local:=True
        
        'Reset alerts
        Application.DisplayAlerts = True
        
        'Close new workbook
        wbCSV.Close
        
        'Increment counters
        lRow = lRow + oSettings.MaxCSV
        iFile = iFile + 1
    Loop
    
End Sub

Sub EmptyTables()
'################################################################
'#
'# Empty all tables in the Workbook except for the config page
'#
'################################################################
    Dim wsPage As Worksheet, loTable As ListObject
    
    For Each wsPage In ThisWorkbook.Worksheets
        For Each loTable In wsPage.ListObjects
            ResetFilters loTable
            If Not wsPage Is shtConfig _
                And Not loTable.DataBodyRange Is Nothing _
                Then loTable.DataBodyRange.Delete
        Next loTable
    Next wsPage
    
End Sub

Private Function RateValidation(ByVal oSettings As clsConfig) As Boolean
'################################################################
'#
'# Compares imported values with country configuration values
'# Outputs the list of unconfigured entries in message box
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Initialize dictionary
    Dim oInvalidDict As Object: Set oInvalidDict = CreateObject("Scripting.Dictionary")
    
    With oSettings.TableDTR
        'Loop through all rows of table
        Dim lRow As Long
        For lRow = 1 To .ListRows.Count
            'If no rate text is defined, log HS value
            If IsEmpty(.ListColumns("complexRate_text").DataBodyRange(lRow)) _
            And IsEmpty(.ListColumns("compoundRate_text").DataBodyRange(lRow)) _
            And IsEmpty(.ListColumns("specificRate_text").DataBodyRange(lRow)) _
            And IsEmpty(.ListColumns("adValoremRate_text").DataBodyRange(lRow)) _
            And IsEmpty(.ListColumns("freeRate_text").DataBodyRange(lRow)) _
            And IsEmpty(.ListColumns("regulation").DataBodyRange(lRow)) _
            And Not oInvalidDict.Exists(.ListColumns("hs").DataBodyRange(lRow).Value) _
            Then oInvalidDict.Add .ListColumns("hs").DataBodyRange(lRow).Value, Nothing
        Next lRow
    End With
    
    'Default if no special conditions to change status
    RateValidation = True
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Rate validation time = " & tEnd & " sec"
    
    'If there are entries with missing rates
    If Not oInvalidDict.Count = 0 Then
        'Build the message
        Dim sMessage As String
        sMessage = "The following HS don't have any rate text or regulation value :" & vbCrLf
        
        Dim vKey As Variant
        For Each vKey In oInvalidDict.keys
            sMessage = sMessage & vbCrLf & vKey
        Next vKey
        
        sMessage = sMessage & vbCrLf & vbCrLf & "Analyse and correct the situation."
        
        'Inform user and update status
        MsgBox sMessage, vbCritical, "Missing rate data"
        RateValidation = False
    End If
    
    'Dispose of dictionary
    Set oInvalidDict = Nothing
        
End Function


Private Function ConfigValidation(ByVal oSettings As clsConfig, _
    ByVal sDataType As String) As Boolean
'################################################################
'#
'# Compares imported values with country configuration values
'# Outputs the list of unconfigured entries in message box
'# ask if we proceed, otherwise it stops the full process
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Define values based on the data type
    Dim sMessage As String, vList As Variant
    Select Case sDataType
        Case "DTR"
            Dim lRow As Long
            For lRow = 1 To oSettings.TableDTR.ListColumns("concat_cg_drt").DataBodyRange.Count
                If Not IsEmpty(oSettings.TableDTR.ListColumns("country_group").DataBodyRange(lRow)) Then _
                    oSettings.TableDTR.ListColumns("concat_cg_drt").DataBodyRange(lRow) = oSettings.TableDTR.ListColumns("country_group").DataBodyRange(lRow) & " " & oSettings.TableDTR.ListColumns("duty_rate_type").DataBodyRange(lRow)
            Next lRow
            
            sMessage = "combinaison of country group and duty rate type"
            vList = GetOppositeList( _
                rRange:=oSettings.TableDTR.ListColumns("concat_cg_drt").DataBodyRange, _
                vInitialList:=oSettings.AllCountryGroupList)
        Case "NOM"
            sMessage = "units of measure"
            vList = GetOppositeList( _
                rRange:=Union(oSettings.TableNOM.ListColumns("alternate_unit_1").DataBodyRange, _
                            oSettings.TableNOM.ListColumns("alternate_unit_2").DataBodyRange, _
                            oSettings.TableNOM.ListColumns("alternate_unit_3").DataBodyRange), _
                vInitialList:=oSettings.UOMDict.keys)
    End Select
    
    'Default if no special conditions to change status
    ConfigValidation = True
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Config validation time = " & tEnd & " sec"
    
    'If there are missing configurations
    If Not IsEmpty(vList) Then
        'Build the message
        sMessage = "The following " & sMessage & " are not in the configuration :" & vbCrLf
        
        Dim vItem As Variant
        For Each vItem In vList
            sMessage = sMessage & vbCrLf & vItem
        Next vItem
        
        sMessage = sMessage & vbCrLf & vbCrLf & "Do you want to proceed?"
        
        'Ask the user if we proceed anyway
        If MsgBox(sMessage, vbYesNo Or vbExclamation, _
            "Proceed?") = vbNo Then ConfigValidation = False
    End If
        
End Function

Private Function GetOppositeList(ByVal rRange As Range, _
    Optional ByVal vInitialList As Variant = Empty) As Variant
'################################################################
'#
'# Takes an array of initial items to compare with a range.
'# Returns the array of items that were in the range but not in
'# the initial list
'#
'################################################################
    'Build initial dictionary of configured items
    Dim oInitialDict As Object: Set oInitialDict = CreateObject("Scripting.Dictionary")
    If Not IsEmpty(vInitialList) Then
        Dim vItem As Variant
        For Each vItem In vInitialList
            oInitialDict.Add vItem, Nothing
        Next vItem
    End If

    'Build opposite dictionary for items to configure
    Dim oOppositeDict As Object: Set oOppositeDict = CreateObject("Scripting.Dictionary")
    With oOppositeDict
        'Loop through all cells of range
        Dim rCell As Range
        For Each rCell In rRange
            'If not in dictionaries, add to opposite dictionary
            If Not oInitialDict.Exists(rCell.Value) _
            And Not .Exists(rCell.Value) _
            Then .Add rCell.Value, Nothing
        Next rCell
        
        'If opposite dictionary not empty, return entries
        If .Count > 0 Then GetOppositeList = .keys
    End With
    
    'Dispose of dictionaries
    Set oInitialDict = Nothing
    Set oOppositeDict = Nothing
    
End Function

Private Function ValidateList(ByVal rRange As Range, _
    ByVal vInitialList As Variant) As Variant
'################################################################
'#
'# Takes an array of initial items to compare with the two first
'# characters of the values in a range.
'# Returns the array of items that were in the range and in
'# the initial list
'#
'################################################################
    'Build initial dictionary of configured items
    Dim oInitialDict As Object: Set oInitialDict = CreateObject("Scripting.Dictionary")
    If Not IsEmpty(vInitialList) Then
        Dim vItem As Variant
        For Each vItem In vInitialList
            oInitialDict.Add vItem, Nothing
        Next vItem
    End If

    'Build valid dictionary for items to configure
    Dim oValidDict As Object: Set oValidDict = CreateObject("Scripting.Dictionary")
    With oValidDict
        'Loop through all cells of range
        Dim rCell As Range
        For Each rCell In rRange
            'If in Initial dictionary, add to valid dictionary
            If oInitialDict.Exists(Left(rCell.Value, 2)) _
            And Not .Exists(Left(rCell.Value, 2)) _
            Then .Add Left(rCell.Value, 2), Nothing
        Next rCell
        
        'If valid dictionary not empty, return entries
        If .Count > 0 Then ValidateList = .keys
    End With
    
    'Dispose of dictionaries
    Set oInitialDict = Nothing
    Set oValidDict = Nothing
    
End Function

Private Sub LaunchProgressBar(ByVal sMessage As String)
'################################################################
'#
'# Initialise and launch UserForm at center of screen
'#
'################################################################
    With ufProgress
        .StartUpPosition = 0
        .Left = Application.Left + (0.5 * Application.Width) - (0.5 * .Width)
        .Top = Application.Top + (0.5 * Application.Height) - (0.5 * .Height)
        .LabelProgress.Width = 0
        .LabelCaption.Caption = sMessage
        .Show
        .Repaint
    End With
End Sub

Private Sub UpdateProgressBar(ByVal sMessage As String, _
    Optional ByVal lIndex As Long = 0, Optional ByVal lMax As Long = 0, _
    Optional ByVal iRefresh As Integer = 0)
'################################################################
'#
'# Update UserForm message and progress status and yields to
'# operation system for every defined iterations
'#
'################################################################
    'Avoid division by 0
    lMax = lMax + 1
    
    With ufProgress
        .LabelProgress.Width = (.FrameProgress.Width) * lIndex / lMax
        .LabelCaption.Caption = sMessage
        .Repaint
    End With
    
    'Yields to operation system ans refresh Excel once every X iterations
    If Not iRefresh = 0 Then If lIndex Mod iRefresh = 0 Then DoEvents
End Sub

Private Sub ResetFilters(ByVal loTable As ListObject)
'################################################################
'#
'# Reset table filters and sort fields
'#
'################################################################
    With loTable
        .Sort.SortFields.Clear
        .Range.AutoFilter
        If Not .ShowAutoFilter Then .Range.AutoFilter
    End With
End Sub

Private Sub CleanseDefinitions(ByVal loTable As ListObject)
'################################################################
'#
'# Remove duplicates from the tables in the definition tab
'#
'################################################################
    'Reset filters
    ResetFilters loTable
    
    'If table not empty
    If Not loTable.DataBodyRange Is Nothing Then
        'Put all column's index in array
        Dim vArray() As Variant: ReDim vArray(loTable.ListColumns.Count - 1) As Variant
        Dim iIndex As Integer
        For iIndex = LBound(vArray) To UBound(vArray)
            vArray(iIndex) = iIndex + 1
        Next iIndex
        'Remove duplicates based on all columns
        loTable.DataBodyRange.RemoveDuplicates vArray, xlYes
    End If
    
End Sub

Private Sub SortColumn(ByVal loTable As ListObject, _
    ByVal sColumnName As String)
'################################################################
'#
'# Apply ascending sort for the specified column in the specified
'# table
'#
'################################################################
    With loTable.Sort
        .SortFields.Add _
            Key:=.Parent.ListColumns(sColumnName).Range, _
            SortOn:=xlSortOnValues, _
            Order:=xlAscending, _
            DataOption:=xlSortNormal
        .Header = xlYes
        .MatchCase = False
        .Orientation = xlTopToBottom
        .SortMethod = xlPinYin
        .Apply
        .SortFields.Clear
    End With
End Sub

Private Function ReplaceChars(ByVal sInitialString As String) As String
'################################################################
'#
'# Replace all unwanted characters from string
'#
'################################################################
    ReplaceChars = Replace(Replace(Replace(Replace(Replace(Replace(Replace(sInitialString, _
        ";", "."), _
        Chr(149), "-"), _
        vbCrLf, " "), _
        vbNewLine, " "), _
        vbCr, " "), _
        vbLf, " "), _
        vbTab, " ")
End Function


