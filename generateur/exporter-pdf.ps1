param([Parameter(Mandatory=$true)][string]$Document, [Parameter(Mandatory=$true)][string]$Pdf)
$ErrorActionPreference = 'Stop'
$wordApplication = $null
$wordDocument = $null
try {
    $wordApplication = New-Object -ComObject Word.Application
    $wordApplication.Visible = $false
    $wordApplication.DisplayAlerts = 0
    $wordApplication.AutomationSecurity = 3
    $wordDocument = $wordApplication.Documents.Open($Document, $false, $false, $false)
    $wordDocument.Repaginate()
    $wordDocument.Fields.Update() | Out-Null
    foreach ($contents in $wordDocument.TablesOfContents) { $contents.Update() }
    $wordDocument.Repaginate()
    foreach ($contents in $wordDocument.TablesOfContents) { $contents.UpdatePageNumbers() }
    foreach ($section in $wordDocument.Sections) {
        foreach ($footer in $section.Footers) { $footer.Range.Fields.Update() | Out-Null }
    }
    $wordDocument.Save()
    # Le onzième argument exporte tous les signets Word, y compris les renvois entre fichiers.
    $wordDocument.ExportAsFixedFormat($Pdf, 17, $false, 0, 0, 1, 1, 0, $true, $true, 2, $true, $true, $false)
} finally {
    if ($null -ne $wordDocument) {
        $wordDocument.Close(0)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordDocument)
    }
    if ($null -ne $wordApplication) {
        $wordApplication.Quit()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordApplication)
    }
}
