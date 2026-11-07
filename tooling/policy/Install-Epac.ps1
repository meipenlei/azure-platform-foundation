[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../.."))
)

$ErrorActionPreference = "Stop"

$versionsPath = Join-Path $RepositoryRoot "foundation/policy/versions.json"
$versions = Get-Content -Raw -Path $versionsPath | ConvertFrom-Json

$moduleName = [string]$versions.epac.module
$moduleVersion = [string]$versions.epac.version
$minimumPowerShell = [version][string]$versions.epac.minimum_powershell

if ($PSVersionTable.PSVersion -lt $minimumPowerShell) {
    throw "APF requires PowerShell $minimumPowerShell or newer for EPAC."
}

$installed = Get-Module -ListAvailable -Name $moduleName |
    Where-Object { $_.Version -eq [version]$moduleVersion } |
    Select-Object -First 1

if (-not $installed) {
    Write-Host "Installing $moduleName $moduleVersion..."
    Install-Module `
        -Name $moduleName `
        -RequiredVersion $moduleVersion `
        -Repository PSGallery `
        -Scope CurrentUser `
        -Force `
        -AllowClobber
}

Import-Module `
    -Name $moduleName `
    -RequiredVersion $moduleVersion `
    -Force

foreach ($command in @(
    "Build-DeploymentPlans",
    "Deploy-PolicyPlan",
    "Deploy-RolesPlan",
    "New-ALZPolicyDefaultStructure",
    "Sync-ALZPolicyFromLibrary"
)) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "EPAC command '$command' is not available."
    }
}

Write-Host "[PASS] $moduleName $moduleVersion is available."
