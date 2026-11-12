<#
.SYNOPSIS
  Creates the WSL distro for the OpenIPSL Linux verification and runs the kit's provisioning steps in it.

.DESCRIPTION
  Reads ..\site.env (KEY=value lines). Creates the distro from the official image with
  "wsl --install <DISTRO_IMAGE> --name <DISTRO_NAME> --no-launch" unless a distro of that name exists.
  Then runs the steps in ..\provision in name order: NN_name.sh as root (wsl -u root, no password),
  NN_name.user.sh as LINUX_USER. The distro is restarted after step 00 so /etc/wsl.conf takes effect.
  Each step's output is also written to ..\logs\<DISTRO_NAME>\<timestamp>_<step>.log.
  Every step checks what is already in place, so running the script again is safe.

.PARAMETER SiteEnv
  The site settings file. Default: site.env in the kit folder.

.PARAMETER Steps
  Two-digit numbers of the steps to run, for example 10,20. Default: all steps.

.PARAMETER SkipCreate
  Do not create the distro; run the steps in the existing one.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File windows\New-VerifyDistro.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File windows\New-VerifyDistro.ps1 -SkipCreate -Steps 20

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File windows\New-VerifyDistro.ps1 -SiteEnv site.nightly.env -Steps 00,10
  A second distro (its name and OM_CHANNEL=nightly in site.nightly.env) with only the base and OpenModelica steps.
#>
[CmdletBinding()]
param(
    [string]$SiteEnv = (Join-Path (Split-Path $PSScriptRoot -Parent) 'site.env'),
    [string[]]$Steps = @(),
    [switch]$SkipCreate
)
$ErrorActionPreference = 'Stop'
$Kit = Split-Path $PSScriptRoot -Parent

function Read-SiteEnv([string]$Path) {
    if (-not (Test-Path $Path)) { throw "site.env not found: $Path (copy site.env.example to site.env and edit it)" }
    $h = @{}
    foreach ($line in Get-Content $Path) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $k = $Matches[1]
            $v = $Matches[2].Trim()
            if ($v -match '^"(.*)"$') { $v = $Matches[1] } elseif ($v -match "^'(.*)'$") { $v = $Matches[1] }
            $h[$k] = $v
        }
    }
    return $h
}

function ConvertTo-WslPath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full -notmatch '^([A-Za-z]):\\(.*)$') { throw "not a local drive path: $full" }
    return '/mnt/' + $Matches[1].ToLower() + '/' + ($Matches[2] -replace '\\', '/')
}

function Get-DistroNames {
    # wsl.exe writes UTF-16; strip the NUL bytes that appear when PowerShell reads it as UTF-8.
    (& wsl.exe --list --quiet) -replace "`0", '' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}

$site = Read-SiteEnv $SiteEnv
foreach ($k in 'DISTRO_NAME', 'DISTRO_IMAGE', 'LINUX_USER') {
    if (-not $site[$k]) { throw "$k is not set in $SiteEnv" }
}
$name = $site['DISTRO_NAME']
$logDir = Join-Path $Kit (Join-Path 'logs' $name)
New-Item -ItemType Directory -Force $logDir | Out-Null

if (-not $SkipCreate) {
    if ((Get-DistroNames) -contains $name) {
        Write-Host "Distro '$name' exists; it is not created again."
    }
    else {
        $a = @('--install', $site['DISTRO_IMAGE'], '--name', $name, '--no-launch')
        if ($site['DISTRO_LOCATION']) { $a += @('--location', $site['DISTRO_LOCATION']) }
        Write-Host "wsl.exe $($a -join ' ')"
        & wsl.exe @a
        if ($LASTEXITCODE -ne 0) { throw "wsl --install failed with exit code $LASTEXITCODE" }
    }
}

$kitWsl = ConvertTo-WslPath $Kit
$siteWsl = ConvertTo-WslPath $SiteEnv
$files = Get-ChildItem (Join-Path $Kit 'provision') -Filter '*.sh' |
    Where-Object { $_.Name -match '^\d\d_' } | Sort-Object Name
# "powershell -File ... -Steps 10,20" passes one string "10,20": split it.
$Steps = @($Steps | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($Steps.Count -gt 0) {
    $files = @($files | Where-Object { $Steps -contains $_.Name.Substring(0, 2) })
    if ($files.Count -eq 0) { throw "no provisioning step matches -Steps $($Steps -join ',')" }
}

foreach ($f in $files) {
    $who = if ($f.Name -like '*.user.sh') { $site['LINUX_USER'] } else { 'root' }
    $log = Join-Path $logDir ("{0}_{1}.log" -f (Get-Date -Format 'yyyyMMddTHHmmss'), $f.BaseName)
    Write-Host "== step $($f.Name) as $who, log $log"
    # Native stderr must not stop the script (Windows PowerShell 5.1 turns it into errors under 'Stop').
    $ErrorActionPreference = 'Continue'
    & wsl.exe -d $name -u $who -- bash "$kitWsl/provision/$($f.Name)" "$siteWsl" 2>&1 |
        ForEach-Object { "$_" } | Tee-Object -FilePath $log
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($code -ne 0) { throw "step $($f.Name) failed with exit code $code; see $log" }
    if ($f.Name -like '00_*') {
        Write-Host "Restarting '$name' so /etc/wsl.conf takes effect."
        & wsl.exe --terminate $name | Out-Null
    }
}
Write-Host "Done. Open a shell in the distro with: wsl -d $name"
