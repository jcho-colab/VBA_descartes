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

Public MappingNOM As String, FileNameNOM As String
Public TableNOM As ListObject, DefinitionNOM As ListObject, FileListNOM As ListObject

Public MappingTXT As String, FileNameTXT As String
Public TableTXT As ListObject, DefinitionTXT As ListObject, FileListTXT As ListObject

Public TableExpHS As ListObject

Public ChapterList As Variant

Public TotalTime As Double
'

Private Sub Class_Initialize()
'################################################################
'#
'# Initialize settings
'#
'################################################################
    'Initialize basic parameters
    Me.Country = shtMenu.Range("Country").Value
    Me.Year = shtMenu.Range("Year").Value
    Me.MinChapter = shtMenu.Range("MinChapter").Value
    
    'Initialize NOM parameters
    Me.MappingNOM = "legal_numbering_exchange"
    Me.FileNameNOM = "HS" & Me.Country & "_EXP_EN_NOM*"
    Set Me.TableNOM = shtNOM.ListObjects("TableNOM")
    Set Me.DefinitionNOM = shtDefinitions.ListObjects("TableNOMDef")
    Set Me.FileListNOM = shtMenu.ListObjects("TableFileListNOM")
    
    'Initialize TXT parameters
    Me.MappingTXT = "texts"
    Me.FileNameTXT = "HS" & Me.Country & "_EXP_EN_TXT*"
    Set Me.TableTXT = shtDefinitions.ListObjects("TableTXT")
    Set Me.DefinitionTXT = shtDefinitions.ListObjects("TableLevelDef")
    Set Me.FileListTXT = shtMenu.ListObjects("TableFileListTXT")
    
    'Initialize country specific parameters (NOM File, Query Tables)
    Select Case Me.Country
        Case "CA"
            Set Me.TableExpHS = shtExpHSCA.ListObjects("ExpHSCA")
        Case "US"
            Me.FileNameNOM = "HSUS_EXP_EN_NOM*"
            Set Me.TableExpHS = shtExpHSUS.ListObjects("ExpHSUS")
    End Select
    
    'Build chapter list
    Dim vChapterList() As Variant: ReDim vChapterList(Me.MinChapter - 2)
    Dim iChapter As Integer
    For iChapter = LBound(vChapterList) To UBound(vChapterList)
        vChapterList(iChapter) = Format(iChapter + 1, "00")
    Next iChapter
    'Define the chapter list parameter
    Me.ChapterList = vChapterList
    
End Sub
