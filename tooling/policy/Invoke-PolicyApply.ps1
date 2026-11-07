[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DefinitionsRootFolder,

    [Parameter(Mandatory = $true)]
    [string]$PacEnvironmentSelector,

    [string]$InputFolder = "./Output",

    [switch]$ConfirmApply
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmApply) {
    throw "Policy apply requires explicit -ConfirmApply."
}

& (Join-Path $PSScriptRoot "Install-Epac.ps1")

if (-not (Test-Path (Join-Path $DefinitionsRootFolder "global-settings.jsonc"))) {
    throw "DefinitionsRootFolder must contain global-settings.jsonc."
}

Deploy-PolicyPlan `
    -DefinitionsRootFolder $DefinitionsRootFolder `
    -PacEnvironmentSelector $PacEnvironmentSelector `
    -InputFolder $InputFolder

Deploy-RolesPlan `
    -DefinitionsRootFolder $DefinitionsRootFolder `
    -PacEnvironmentSelector $PacEnvironmentSelector `
    -InputFolder $InputFolder

Write-Host "[PASS] EPAC policy and role plans applied."
