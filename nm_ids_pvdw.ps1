########################
#
# 1) nm

. "config.ps1"

$SYNTAX_ = "Syntax: #[nm_]START #[COUNT | [nm_]END] #[quality]"

$MYWORKDIR = "./"
$SCRIPT_PATH = "ids.py"

$par1 = New-Object System.Collections.ArrayList

$par1.Add($SCRIPT_PATH) > $null
$par1.Add("-path") > $null
$par1.Add($MYWORKDIR) > $null

$startTime = Get-Date -Format $TimeFormat

$start = [Int32]($args[0] -replace "^nm_",'')
$count = [Int32]($args[1] -replace "^nm_",'')
$quality = [String]($args[2])
$proxy = [String]($args[3])

if ($start -lt 1 -or $start -gt 100000)
{ write($SYNTAX_); return }
if ($count -eq $null -or $count -eq 0)
{ $count = 1 }
if ($count -lt 1 -or $count -gt 100000)
{ write($SYNTAX_); return }

if ($quality -eq "")
{ $quality = "360p" }

if ($count -gt $start)
{ $end = $count; }
else
{ $end = $start + $count }

$par1.Add("-start") > $null
$par1.Add($start) > $null
$par1.Add("-end") > $null
$par1.Add($end - 1) > $null
$par1.Add("-max_quality") > $null
$par1.Add($quality) > $null
if ($proxy -ne "")
{
    $par1.Add("-proxy") > $null
    $par1.Add($proxy) > $null
}

write ("Starting nm from " + $start + " to " + ($end-1) + " (" + ($end - $start) + ")")

(&"$RUN_PYTHON3" $par1)

$endTime = Get-Date -Format $TimeFormat
$timestr = "Started at " + $startTime + ", ended at " + $endTime
write $timestr

#
########################
