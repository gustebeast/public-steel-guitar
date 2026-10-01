# Run a command BELOW NORMAL priority, capture its output, and return its exit code.
#
# ⚠ `cmd /c start /low /b /wait "" prog args` DOES NOT WORK and fails SILENTLY. Without
# /b the empty "" is the window title and the form is correct; WITH /b there is no window,
# start takes that "" as the program to run, runs nothing, and exits 0. Six routes then
# "finished" in 79 seconds and the fan printed six tidy rows of empty results.
# Dropping the "" is not a fix either: the program path contains spaces, so a quoted first
# argument is ambiguous with the title again.
#
# Start-Process has no priority parameter, but -PassThru hands back the object, and
# PriorityClass can be set before the process gets far. Child processes INHERIT it, which
# is the point: the cost is the java the router spawns, not this launcher.
param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [Parameter(Mandatory = $true)][string]$Log,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
)
$p = Start-Process -FilePath $Exe -ArgumentList $Args -PassThru -NoNewWindow `
                   -RedirectStandardOutput $Log -RedirectStandardError "$Log.err"
try { $p.PriorityClass = 'BelowNormal' } catch { }   # may already have exited
$p.WaitForExit()
if (Test-Path "$Log.err") { Get-Content "$Log.err" | Add-Content $Log; Remove-Item "$Log.err" }
exit $p.ExitCode
