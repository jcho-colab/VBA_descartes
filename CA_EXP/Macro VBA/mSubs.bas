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

Sub DeleteEntries(ByVal oSettings As clsConfig)
'################################################################
'#
'# Delete the unnecessary entries with a progress bar update
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Set column name
    Dim sColumnName As String: sColumnName = "hs"
    
    'Initialise progress bar
    LaunchProgressBar "Fetching " & sColumnName & " details"
    
    'Reset filters
    ResetFilters oSettings.TableNOM
    
    'Define criterias
    Dim vCriterias As Variant: vCriterias = ValidateList( _
        rRange:=oSettings.TableNOM.ListColumns(sColumnName).DataBodyRange, _
        vInitialList:=oSettings.ChapterList)
    
    'Skip if no criteria to remove
    If Not IsEmpty(vCriterias) Then
        'Update progress bar
        UpdateProgressBar "Sorting by " & sColumnName
        
        'Sort by criteria for faster deletion, fewer areas
        SortColumn oSettings.TableNOM, sColumnName
        
        'Loop through criterias
        Dim iCriteria As Integer
        For iCriteria = LBound(vCriterias) To UBound(vCriterias)
            'Adjust the criteria output
            vCriterias(iCriteria) = "=" & vCriterias(iCriteria) & "*"
            
            'Update progress bar
            UpdateProgressBar "Deleting " & sColumnName & " " & vCriterias(iCriteria) & " entries", _
                iCriteria, UBound(vCriterias), 5
            
            'Set the filter for the unwanted values
            oSettings.TableNOM.Range.AutoFilter _
                Field:=oSettings.TableNOM.ListColumns(sColumnName).Index, _
                Criteria1:=vCriterias(iCriteria)
                
            'Delete the unwanted values
            oSettings.TableNOM.DataBodyRange.SpecialCells(xlCellTypeVisible).EntireRow.Delete
        Next iCriteria
        
        'Reset filters
        oSettings.TableNOM.AutoFilter.ShowAllData
    End If
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Delete " & sColumnName & " time = " & tEnd & " sec"
    
End Sub

Sub ProcessHS(ByVal oSettings As clsConfig)
'################################################################
'#
'# Remove double leading zeros on HS with a progress bar update
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Initialise progress bar
    LaunchProgressBar "Fetching HS details"
    
    'Reset filters
    ResetFilters oSettings.TableNOM
    
    'Skip if no double leading zeros
    If Not IsEmpty(ValidateList( _
        rRange:=oSettings.TableNOM.ListColumns("hs").DataBodyRange, _
        vInitialList:=Array("00"))) Then
        
        'Update progress bar
        UpdateProgressBar "Sorting and filtering HS"
        
        'Sort by HS for faster process, fewer areas
        SortColumn oSettings.TableNOM, "hs"
        
        'Filter HS with double leading zeros only
        oSettings.TableNOM.Range.AutoFilter _
            Field:=oSettings.TableNOM.ListColumns("hs").Index, _
            Criteria1:="=00*"
        
        'Loop through all visible rows in table
        With oSettings.TableNOM.ListColumns("hs").DataBodyRange.SpecialCells(xlCellTypeVisible)
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
        oSettings.TableNOM.AutoFilter.ShowAllData
    End If
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "Process HS time = " & tEnd & " sec"
    
End Sub

Sub FlagHS(ByVal oSettings As clsConfig)
'################################################################
'#
'# Flag HS values to query valid last update only, with
'# progress bar update
'#
'# Flags : 01-active, 02-invalid, 03-duplicate
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Initialise progress bar
    LaunchProgressBar "Sorting data to flag HS"
    
    'Reset filters
    ResetFilters oSettings.TableNOM
    
    'Sort data by priority
    With oSettings.TableNOM.Sort
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
        .Header = xlYes
        .MatchCase = False
        .Orientation = xlTopToBottom
        .SortMethod = xlPinYin
        .Apply
        .SortFields.Clear
    End With
        
    'Update progress bar
    UpdateProgressBar "Flagging HS"
    
    'Initialize dictionary
    Dim oHSDict As Object: Set oHSDict = CreateObject("Scripting.Dictionary")
    
    'Loop through all visible cells of column
    Dim rCell As Range
    For Each rCell In oSettings.TableNOM.ListColumns("hs").DataBodyRange.SpecialCells(xlCellTypeVisible).Cells
        'rCell relative index
        Dim lIndex As Long: lIndex = rCell.Row - rCell.ListObject.Range.Row
        
        'If not in dictionary, add it and check valid_to date
        If Not oHSDict.Exists(rCell.Value) Then
            oHSDict.Add rCell.Value, Nothing
            'If valid_to date is within the processed year, flag as active
            If Left(oSettings.TableNOM.ListColumns("valid_to").DataBodyRange(lIndex).Value, 4) >= oSettings.Year Then
                oSettings.TableNOM.ListColumns("hs_flag").DataBodyRange(lIndex).Value = "01-active"
            'If valid_to date is earlier then start of processed year, flag as invalid
            Else: oSettings.TableNOM.ListColumns("hs_flag").DataBodyRange(lIndex).Value = "02-invalid"
            End If
        'If in dictionary, flag as duplicate
        Else: oSettings.TableNOM.ListColumns("hs_flag").DataBodyRange(lIndex).Value = "03-duplicate"
        End If
    Next rCell

    'Dispose of dictionary
    Set oHSDict = Nothing

    'Reset filters
    oSettings.TableNOM.AutoFilter.ShowAllData
    
    'Update progress bar
    UpdateProgressBar "Sorting by HS"
    
    'Sort data by HS
    SortColumn oSettings.TableNOM, "hs"
    
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
            
            'If not in dictionary, add it
            If Not oDescriptionDict.Exists(.ListColumns("id").DataBodyRange(lRow).Value) Then
                oDescriptionDict.Add .ListColumns("id").DataBodyRange(lRow).Value, _
                    .ListColumns("full_description").DataBodyRange(lRow).Value
            'If in dictionary, change the item value (full_description)
            Else: oDescriptionDict.Item(.ListColumns("id").DataBodyRange(lRow).Value) = _
                    .ListColumns("full_description").DataBodyRange(lRow).Value
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

Sub QueryOutput(ByVal oSettings As clsConfig)
'################################################################
'#
'# Refresh query table and adjust values with progress bar update
'#
'################################################################
    'Start timer
    Dim tStart As Double: tStart = Timer
    
    'Initialise progress bar
    mSubs.LaunchProgressBar "Updating Export HS query table"
    
    'Refresh query table
    oSettings.TableExpHS.QueryTable.Refresh BackgroundQuery:=False
    
    'Close progress bar
    Unload ufProgress
    
    'Output processing time
    Dim tEnd As Double: tEnd = Timer - tStart
    oSettings.TotalTime = oSettings.TotalTime + tEnd
    Debug.Print "PGA update time = " & tEnd & " sec"
End Sub

Sub ExportXLSX(ByVal oSettings As clsConfig)
'################################################################
'#
'# Export the full table in XLSX file
'#
'################################################################
    'Find unique file name
    Dim sFileName As String: sFileName = ThisWorkbook.Path & Application.PathSeparator & _
        "XLSX" & Application.PathSeparator & "UPLOAD " & oSettings.TableExpHS.Name & " V"
    Dim iVersion As Integer: iVersion = 1
    Do While Dir(sFileName & iVersion & ".xlsx") <> ""
        iVersion = iVersion + 1
    Loop
    
    'Set final file name version
    sFileName = sFileName & iVersion
    
    'Create a new workbook
    Dim wbXLSX As Workbook: Set wbXLSX = Workbooks.Add
        
    'Copy-Paste table
    oSettings.TableExpHS.Range.Copy wbXLSX.Sheets(1).Cells(1, 1)
    
    'Don't ask and overwrite output if exist
    Application.DisplayAlerts = False
    
    'Save XLSX file
    wbXLSX.SaveAs Filename:=sFileName & ".xlsx", FileFormat:=xlOpenXMLWorkbook, CreateBackup:=False
    
    'Reset alerts
    Application.DisplayAlerts = True
    
    'Close new workbook
    wbXLSX.Close
    
End Sub

Sub EmptyTables()
'################################################################
'#
'# Empty all tables in the Workbook
'#
'################################################################
    Dim wsPage As Worksheet, loTable As ListObject
    
    For Each wsPage In ThisWorkbook.Worksheets
        For Each loTable In wsPage.ListObjects
            ResetFilters loTable
            If Not loTable.DataBodyRange Is Nothing _
                Then loTable.DataBodyRange.Delete
        Next loTable
    Next wsPage
    
End Sub

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
