param(
    [ValidateSet('Set', 'Get', 'List', 'Remove')]
    [string]$Action = 'List',
    [ValidatePattern('^[a-z0-9][a-z0-9-]{1,62}$')]
    [string]$Alias,
    [string]$Username = 'root'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$vaultRoot = Join-Path $repoRoot '.secrets\server-credentials'

switch ($Action) {
    'List' {
        if (-not (Test-Path -LiteralPath $vaultRoot)) { return }
        Get-ChildItem -LiteralPath $vaultRoot -File -Filter '*.credential.xml' |
            ForEach-Object { $_.BaseName -replace '\.credential$', '' }
    }
    'Set' {
        if (-not $Alias) { throw 'Alias is required for Set.' }
        New-Item -ItemType Directory -Force -Path $vaultRoot | Out-Null
        $credential = Get-Credential -UserName $Username -Message "Credential for $Alias"
        $target = Join-Path $vaultRoot "$Alias.credential.xml"
        $credential | Export-Clixml -LiteralPath $target
        Write-Output "Stored encrypted credential alias: $Alias"
    }
    'Get' {
        if (-not $Alias) { throw 'Alias is required for Get.' }
        $target = Join-Path $vaultRoot "$Alias.credential.xml"
        if (-not (Test-Path -LiteralPath $target)) { throw "Credential alias not found: $Alias" }
        Import-Clixml -LiteralPath $target
    }
    'Remove' {
        if (-not $Alias) { throw 'Alias is required for Remove.' }
        $target = Join-Path $vaultRoot "$Alias.credential.xml"
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target
            Write-Output "Removed credential alias: $Alias"
        }
    }
}
