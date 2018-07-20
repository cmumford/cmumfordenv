############################################################################## 
## 
## Invoke-CmdScript.ps1 
## 
## Invoke the specified batch file (and parameters), but also propigate any 
## environment variable changes back to the PowerShell environment that 
## called it. 
## 
## ie: 
## 
## PS > type foo-that-sets-the-FOO-env-variable.cmd 
## @set FOO=%* 
## echo FOO set to %FOO%. 
##  
## PS > $env:FOO 
##  
## PS > Invoke-CmdScript "foo-that-sets-the-FOO-env-variable.cmd" Test
##  
## C:\Temp>echo FOO set to Test. 
## FOO set to Test. 
##  
## PS > $env:FOO 
## Test 
## 
############################################################################## 

param([string] $script, [string] $parameters) 

$tempFile = [IO.Path]::GetTempFileName() 

## Store the output of cmd.exe.  We also ask cmd.exe to output  
## the environment table after the batch file completes 

cmd /c " `"$script`" $parameters && set > `"$tempFile`" "

## Go through the environment variables in the temp file. 
## For each of them, set the variable in our local environment. 
Get-Content $tempFile | Foreach-Object {  
    if($_ -match "^(.*?)=(.*)$") 
    {
        Set-Content "env:\$($matches[1])" $matches[2] 
    }
} 

Remove-Item $tempFile