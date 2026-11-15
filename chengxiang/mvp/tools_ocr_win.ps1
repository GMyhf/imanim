# Windows built-in OCR (Windows.Data.Pdf render + Windows.Media.Ocr) for scanned textbook PDFs.
# Writes corpus-format text directly: "===== 第 N 页 =====" markers (no tools_corpus step needed).
#
# Usage (Windows PowerShell 5.1):
#   powershell -NoProfile -File tools_ocr_win.ps1 -Pdf <file.pdf> -Out <slug.txt> [-First 1] [-Last 0] [-Lang zh-Hans-CN] [-Width 2000]
# -Last 0 means to the end. Output is resumable: pages already present in -Out are skipped.
param(
    [Parameter(Mandatory = $true)][string]$Pdf,
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$First = 1,
    [int]$Last = 0,
    [string]$Lang = "zh-Hans-CN",
    [int]$Width = 2000
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$ext = [System.WindowsRuntimeSystemExtensions]
$asOp = $ext.GetMethods() | Where-Object { $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
$asAct = $ext.GetMethods() | Where-Object { $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq "IAsyncAction" } | Select-Object -First 1
function Await($op, [type]$type) {
    $t = $asOp.MakeGenericMethod($type).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result
}
function AwaitAction($act) { $t = $asAct.Invoke($null, @($act)); $t.Wait(-1) | Out-Null }

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($Lang))
if ($null -eq $engine) { throw "OCR language not available: $Lang" }

$full = (Resolve-Path -LiteralPath $Pdf).Path
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($full)) ([Windows.Storage.StorageFile])
$doc = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
$total = [int]$doc.PageCount
if ($Last -le 0 -or $Last -gt $total) { $Last = $total }

$done = @{}
if (Test-Path -LiteralPath $Out) {
    foreach ($m in [regex]::Matches([IO.File]::ReadAllText($Out, [Text.Encoding]::UTF8), "(?m)^=+ \S+ (\d+) \S+ =*$")) { $done[[int]$m.Groups[1].Value] = $true }
}
$cjk = "[\u2e80-\u9fff\u3000-\u303f\uff00-\uffef]"
$gap = "(?<=$cjk)[ \t]+(?=$cjk)"
$enc = New-Object System.Text.UTF8Encoding($false)
$sw = New-Object System.IO.StreamWriter($Out, $true, $enc)
$mark = [string]([char]0x7B2C)   # first char of the page marker keyword
$yeChar = [string]([char]0x9875)
try {
    for ($i = $First; $i -le $Last; $i++) {
        if ($done.ContainsKey($i)) { continue }
        $page = $doc.GetPage([uint32]($i - 1))
        $opts = New-Object Windows.Data.Pdf.PdfPageRenderOptions
        $opts.DestinationWidth = [uint32]$Width
        $ms = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
        AwaitAction ($page.RenderToStreamAsync($ms, $opts))
        $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($ms)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $res = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
        $lines = foreach ($l in $res.Lines) { [regex]::Replace($l.Text, $gap, "") }
        $sw.WriteLine("===== " + $mark + " $i " + $yeChar + " =====")
        $sw.WriteLine(($lines -join "`n"))
        $sw.WriteLine()
        $sw.Flush()
        $bmp.Dispose(); $ms.Dispose(); $page.Dispose()
        if (($i % 20) -eq 0) { Write-Host "page $i / $Last" }
    }
}
finally { $sw.Dispose() }
Write-Host "done: $Out ($total pages in pdf, range $First-$Last)"
