VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "clsConfig"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit 'Force explicit variable declaration

Public Country As String, Year As String
Public MinChapter As Integer
Public MaxCSV As Long
Public ZD14Date As Date

Public MappingDTR As String, FileNameDTR As String
Public TableDTR As ListObject, DefinitionDTR As ListObject, FileListDTR As ListObject

Public MappingNOM As String, FileNameNOM As String
Public TableNOM As ListObject, DefinitionNOM As ListObject, FileListNOM As ListObject

Public MappingTXT As String, FileNameTXT As String
Public TableTXT As ListObject, DefinitionTXT As ListObject, FileListTXT As ListObject

Public TableZD14 As ListObject, TableZD14Test As ListObject
Public TableCAPDR As ListObject, TableMX6Digits As ListObject
Public TableZZDE As ListObject, TableZZDF As ListObject

Public AllCountryGroupList As Variant, ActiveCountryGroupList As Variant
Public ChapterList As Variant, CountryList As Variant
Public UOMDict As Object

Public TotalTime As Double
'

Private Sub Class_Initialize()
'################################################################
'#
'# Initialize settings and read country speficic config tables
'# from the config worksheet
'#
'################################################################
    'Initialize basic parameters
    Me.Country = shtMenu.Range("Country").Value
    Me.Year = shtMenu.Range("Year").Value
    Me.MinChapter = shtMenu.Range("MinChapter").Value
    Me.MaxCSV = shtMenu.Range("MaxCSV").Value
    Me.ZD14Date = shtMenu.Range("ZD14Date").Value
    
    'Initialize DTR parameters
    Me.MappingDTR = "duty_rate"
    Me.FileNameDTR = "HS" & shtConfig.Range(Me.Country & "CountryCode").Value & "_IMP_EN_DTR*"
    Set Me.TableDTR = shtDTR.ListObjects("TableDTR")
    Set Me.DefinitionDTR = shtDefinitions.ListObjects("TableCountryGroupDef")
    Set Me.FileListDTR = shtMenu.ListObjects("TableFileListDTR")
    
    'Initialize NOM parameters
    Me.MappingNOM = "legal_numbering_exchange"
    Me.FileNameNOM = "HS" & shtConfig.Range(Me.Country & "CountryCode").Value & "_IMP_EN_NOM*"
    Set Me.TableNOM = shtNOM.ListObjects("TableNOM")
    Set Me.DefinitionNOM = shtDefinitions.ListObjects("TableOgaCodeDef")
    Set Me.FileListNOM = shtMenu.ListObjects("TableFileListNOM")
    
    'Initialize TXT parameters
    Me.MappingTXT = "texts"
    Me.FileNameTXT = "HS" & shtConfig.Range(Me.Country & "CountryCode").Value & "_IMP_EN_TXT*"
    Set Me.TableTXT = shtDefinitions.ListObjects("TableTXT")
    Set Me.DefinitionTXT = shtDefinitions.ListObjects("TableLevelDef")
    Set Me.FileListTXT = shtMenu.ListObjects("TableFileListTXT")
    
    'Initialize Query Tables parameters
    Set Me.TableZD14 = shtZD14.ListObjects("_ZD14")
    Set Me.TableCAPDR = shtCAPDR.ListObjects("CAPDR")
    Set Me.TableMX6Digits = shtMX6Digits.ListObjects("MX6Digits")
    Set Me.TableZZDE = shtZZDE.ListObjects("ZZDE")
    Set Me.TableZZDF = shtZZDF.ListObjects("ZZDF")
    Set Me.TableZD14Test = shtZD14Test.ListObjects("ZD14Test")
    
    'Build country group lists
    With shtConfig.ListObjects(Me.Country & "RateType")
        'Loop through all rows of country rate type table
        Dim vAllCountryGroupList() As Variant: ReDim vAllCountryGroupList(.ListRows.Count - 1)
        Dim vActiveCountryGroupList() As Variant: ReDim vActiveCountryGroupList(.ListRows.Count - 1)
        Dim iRateType As Integer, iActive As Integer: iActive = 0
        For iRateType = LBound(vAllCountryGroupList) To UBound(vAllCountryGroupList)
            'Add all country groups to all list
            vAllCountryGroupList(iRateType) = .ListColumns("Descartes CG").DataBodyRange(iRateType + 1).Value
            'Add only desired country groups to active list
            If Not .ListColumns("Comment").DataBodyRange(iRateType + 1).Value = "remove" Then
                vActiveCountryGroupList(iActive) = .ListColumns("Descartes CG").DataBodyRange(iRateType + 1).Value
                iActive = iActive + 1
            End If
        Next iRateType
    End With
    'Remove empty values from active list
    ReDim Preserve vActiveCountryGroupList(iActive - 1)
    'Define the counrty group list parameters
    Me.AllCountryGroupList = vAllCountryGroupList
    Me.ActiveCountryGroupList = vActiveCountryGroupList
    
    'Build chapter list
    Dim vChapterList() As Variant: ReDim vChapterList(Me.MinChapter - 2)
    Dim iChapter As Integer
    For iChapter = LBound(vChapterList) To UBound(vChapterList)
        vChapterList(iChapter) = Format(iChapter + 1, "00")
    Next iChapter
    'Define the chapter list parameter
    Me.ChapterList = vChapterList
    
    'Build country list
    Select Case Me.Country
        Case "EU"
            With shtConfig.ListObjects(Me.Country & "CountryList")
                'Loop through all rows of country list table
                Dim vCountryList() As Variant: ReDim vCountryList(.ListRows.Count - 1)
                Dim iCountry As Integer
                For iCountry = LBound(vCountryList) To UBound(vCountryList)
                    'Add all countries to array
                    vCountryList(iCountry) = .DataBodyRange(iCountry + 1).Value
                Next iCountry
            End With
            'Define the counrty list parameter
            Me.CountryList = vCountryList
        Case Else
            'Define the counrty list parameter
            Me.CountryList = Array(Me.Country)
    End Select
    
    'Build unit of measure dictionary
    Set Me.UOMDict = CreateObject("Scripting.Dictionary")
    With shtConfig.ListObjects(Me.Country & "UOM")
        'Loop through all rows of country unit of measure table
        Dim iUOM As Integer
        For iUOM = 1 To .ListRows.Count
            'Add all units of measure to dictionary
            Me.UOMDict.Add .ListColumns("Descartes UOM").DataBodyRange(iUOM).Value, _
                .ListColumns("SAP UOM").DataBodyRange(iUOM).Value
        Next iUOM
    End With
    
    
End Sub
