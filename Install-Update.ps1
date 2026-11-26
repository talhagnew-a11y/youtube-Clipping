param([string]$InstallRoot,[switch]$CheckOnly,[switch]$NoRestart)
$ErrorActionPreference='Stop'
if(-not $InstallRoot){
 Add-Type -AssemblyName System.Windows.Forms
 $picker=New-Object System.Windows.Forms.FolderBrowserDialog
 $picker.Description='Choose the EXISTING shortsflow folder (contains python, venv, models).'
 if($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){return}
 $InstallRoot=$picker.SelectedPath
}
& (Join-Path $PSScriptRoot 'Apply-ShortsFlow-Update.ps1') -InstallRoot $InstallRoot -PackageRoot $PSScriptRoot -CheckOnly:$CheckOnly -NoRestart:$NoRestart
