# Verify PowerShell files parse on the Windows CI runner without executing side effects.
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$scripts=@(Get-ChildItem (Join-Path $root "scripts") -Filter "*.ps1" -File)
$scripts+=@(Get-ChildItem $root -Filter "*.ps1" -File)
$bad=@()
foreach ($script in $scripts) {
    $tokens=$null
    $errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $script.FullName,[ref]$tokens,[ref]$errors)
    if (@($errors).Count -gt 0) {
        $bad+= $script.Name
        # Diagnostic metadata only, never untrusted source code or error text.
        foreach ($issue in @($errors)) {
            Write-Host ("PS_PARSE_ERROR:"+$script.Name+":line="+$issue.Extent.StartLineNumber+":id="+$issue.ErrorId)
        }
    }
}
if ($bad.Count -gt 0) {
    Write-Host ("POWERSHELL_SYNTAX_FAILED_COUNT="+$bad.Count)
    $bad | ForEach-Object { Write-Host ("INVALID_PS1: "+$_) }
    exit 2
}
Write-Host ("POWERSHELL_SYNTAX_PASS_COUNT="+$scripts.Count)
