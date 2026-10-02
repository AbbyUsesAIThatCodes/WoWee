param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Destination
)
$ErrorActionPreference = 'Stop'
$Source = (Resolve-Path -LiteralPath $Source).Path
$Destination = (Resolve-Path -LiteralPath $Destination).Path
# The startup inventory also checks these physical directories. These links
# are for existing asset reads; the private tables and FrameXML stay copies.
# The review package deliberately contains no asset extraction/import tools.
foreach ($name in 'dbfilesclient','world','character','creature') {
    $asset = Join-Path $Source $name
    $view = Join-Path $Destination $name
    if (-not (Test-Path -LiteralPath $asset -PathType Container)) {
        throw "Source extraction is missing $name"
    }
    if (Test-Path -LiteralPath $view) { throw "Destination already contains $name" }
    New-Item -ItemType Junction -Path $view -Target $asset | Out-Null
}
