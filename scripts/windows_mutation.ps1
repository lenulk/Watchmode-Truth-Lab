param(
    [Parameter(Mandatory=$true)][string]$WorkspacePath,
    [Parameter(Mandatory=$true)][string]$TargetPath,
    [Parameter(Mandatory=$true)][string]$Mode,
    [Parameter(Mandatory=$true)][string]$ContentBase64,
    [Parameter(Mandatory=$true)][string]$IntermediateBase64,
    [ValidateSet('UNC','MountedWindows')][string]$AccessMode = 'UNC'
)
$ErrorActionPreference = 'Stop'
$workspaceResolved = [IO.Path]::GetFullPath($WorkspacePath).TrimEnd('\') + '\'
$targetResolved = [IO.Path]::GetFullPath($TargetPath)
if ($AccessMode -eq 'UNC' -and
    -not $workspaceResolved.StartsWith('\\wsl.localhost\', [StringComparison]::OrdinalIgnoreCase) -and
    -not $workspaceResolved.StartsWith('\\wsl$\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Expected a WSL UNC fixture workspace'
}
if ($AccessMode -eq 'MountedWindows' -and $workspaceResolved -notmatch '^[A-Za-z]:\\') {
    throw 'Expected a mounted Windows drive fixture workspace'
}
if (-not $targetResolved.StartsWith($workspaceResolved, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Mutation target escapes fixture workspace'
}
$content = [Convert]::FromBase64String($ContentBase64)
switch ($Mode) {
    'overwrite' { [IO.File]::WriteAllBytes($targetResolved, $content) }
    'burst' {
        [IO.File]::WriteAllBytes($targetResolved, [Convert]::FromBase64String($IntermediateBase64))
        [IO.File]::WriteAllBytes($targetResolved, $content)
    }
    'atomic_replace' {
        Add-Type @'
using System.Runtime.InteropServices;
public static class WTLMove {
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern bool MoveFileEx(string source, string target, uint flags);
}
'@
        $temporaryPath = $targetResolved + '.wtl-' + [Guid]::NewGuid().ToString('N')
        try {
            [IO.File]::WriteAllBytes($temporaryPath, $content)
            if (-not [WTLMove]::MoveFileEx($temporaryPath, $targetResolved, 1)) {
                throw (New-Object ComponentModel.Win32Exception([Runtime.InteropServices.Marshal]::GetLastWin32Error()))
            }
        } finally {
            if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath -Force }
        }
    }
    default { throw 'Unsupported mutation mode' }
}
