[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DefinitionsRootFolder,

    [Parameter(Mandatory = $true)]
    [string]$PacEnvironmentSelector,

    [string]$OutputFolder = "./Output"
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "Install-Epac.ps1")

if (-not (Test-Path (Join-Path $DefinitionsRootFolder "global-settings.jsonc"))) {
    throw "DefinitionsRootFolder must contain global-settings.jsonc."
}

New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null

Build-DeploymentPlans `
    -DefinitionsRootFolder $DefinitionsRootFolder `
    -PacEnvironmentSelector $PacEnvironmentSelector `
    -OutputFolder $OutputFolder

Write-Host "[PASS] EPAC deployment plans built in $OutputFolder."
