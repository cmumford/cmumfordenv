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
function Invoke-CmdScript( [string] $script, [string] $parameters )
{
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
}

Invoke-CmdScript "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" x86

Set-PSDebug -strict

########################################################
# General utility
# Add-PSSnapin PSCX

$pf86 = ${env:ProgramFiles(x86)}
# There's no env var to refer to Program Files
$pf = "$env:HOMEDRIVE\Program Files"

Set-alias editplus "$pf86\EditPlus 2\editplus.exe"
Set-alias msbuild "C:\Windows\Microsoft.NET\Framework\v2.0.50727\MSBuild.exe"
set-alias installutil $env:windir\Microsoft.NET\Framework\v2.0.50727\installutil
Set-alias wilogutl "$pf\Microsoft SDKs\Windows\v6.0\Bin\WiLogUtl.exe"
Set-alias gitl "git log --graph --decorate --pretty=oneline --abbrev-commit"
Set-alias gitlog "git log --graph --decorate --pretty=medium --abbrev-commit"
Set-alias gitdiff "git diff --no-ext-diff"
set-alias meld "$pf86\Meld\meld\meld.exe"
Set-alias python3 "C:\Users\cmumford\AppData\Local\Programs\Python\Python35-32\python.exe"

function xp       { explorer "$pwd" }
function ss       { . $profile }
function cfind	  { C:\chris\cmumford\src\cfind\bin\Release\cfind.exe $args }
function windir   { Out-Clipboard $pwd }
########################################################


########################################################
# General software cevelopment stuff
function hgrep { compgrep '--include="*.h"' $args }
function cgrep { compgrep '--include="*.cpp"' '--include="*.c"' $args }
function chgrep { compgrep '--include="*.cpp"' '--include="*.c"' '--include="*.h"' $args }
function csgrep { compgrep '--include="*.cs"' $args }
########################################################


########################################################
# 'g' command and targets
$GLOBAL:go_locations = @{};

function g ([string] $location) {
	if( $go_locations.ContainsKey($location) ) {
		set-location $go_locations[$location];
	} else {
		write-output "The following locations are defined:";
		write-output $go_locations;
	}
}

$workspace = "D:\src\chromium\src";
$go_locations.Clear()
$go_locations.Add("home", "C:\Users\cmumford")
$go_locations.Add("chris", "C:\Users\cmumford")
$go_locations.Add("src", "C:\Users\cmumford\src")
$go_locations.Add("c", "$workspace")
$go_locations.Add("t", "$workspace\third_party")
$go_locations.Add("b", "$workspace\third_party\WebKit")
$go_locations.Add("l", "$workspace\third_party\leveldatabase")
$go_locations.Add("snappy", "$workspace\third_party\snappy\src")
########################################################

[Environment]::SetEnvironmentVariable("gomadir", "C:\Users\cmumford\goma-win64")

# For the Monokai color scheme
# https://github.com/ntwb/posh-monokai
# "C:\Users\cmumford\src\posh-monokai\posh-monokai.ps1"

# SIG # Begin signature block
# MIIEMwYJKoZIhvcNAQcCoIIEJDCCBCACAQExCzAJBgUrDgMCGgUAMGkGCisGAQQB
# gjcCAQSgWzBZMDQGCisGAQQBgjcCAR4wJgIDAQAABBAfzDtgWUsITrck0sYpfvNR
# AgEAAgEAAgEAAgEAAgEAMCEwCQYFKw4DAhoFAAQUfxzdA4qEGmwfgLRdb23NodE4
# tiagggI9MIICOTCCAaagAwIBAgIQ+Rwgva+K/ZtHdcCJSXYANjAJBgUrDgMCHQUA
# MCwxKjAoBgNVBAMTIVBvd2VyU2hlbGwgTG9jYWwgQ2VydGlmaWNhdGUgUm9vdDAe
# Fw0xMTAxMDkwMTI5NThaFw0zOTEyMzEyMzU5NTlaMBoxGDAWBgNVBAMTD1Bvd2Vy
# U2hlbGwgVXNlcjCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAqLc11pt2wKfn
# vxERuOyyYtZ4M9U4oEEacL7JKOv5Z7ks8nfGfTiIdjLbuAs2SEwF3kcDRN4XY+Y4
# AOsrZgtxTdxOfF/aEXdEaF4YHhPswuvTS8w+DIOGLof3ti/Ft/FFKMo3XYsVcbPa
# xKl2Ptmu0u7nzKaZQeck/RelqaSQqGMCAwEAAaN2MHQwEwYDVR0lBAwwCgYIKwYB
# BQUHAwMwXQYDVR0BBFYwVIAQI33N1GVFm2E+A7i3nSA3UKEuMCwxKjAoBgNVBAMT
# IVBvd2VyU2hlbGwgTG9jYWwgQ2VydGlmaWNhdGUgUm9vdIIQCQHeBqbQ3LdEPawb
# crAcKjAJBgUrDgMCHQUAA4GBAFCkb0rABvUlp7aGAQsqogQhFXZstGSC524sGmuw
# CYY9yWzf/gt11cvDD+XGezZxOggjTlH79gLioYKEYN+hT/zQ052t7c7w/KzDSxsf
# HUHtVMLdb/ow7AQ7th1LmYn3T9tGCAB9ap0Y9NJemwovd6xhenBasQweKwXVhgMR
# mBdRMYIBYDCCAVwCAQEwQDAsMSowKAYDVQQDEyFQb3dlclNoZWxsIExvY2FsIENl
# cnRpZmljYXRlIFJvb3QCEPkcIL2viv2bR3XAiUl2ADYwCQYFKw4DAhoFAKB4MBgG
# CisGAQQBgjcCAQwxCjAIoAKAAKECgAAwGQYJKoZIhvcNAQkDMQwGCisGAQQBgjcC
# AQQwHAYKKwYBBAGCNwIBCzEOMAwGCisGAQQBgjcCARUwIwYJKoZIhvcNAQkEMRYE
# FAayKvpDgWSVLjF0Avb65u8yNUY8MA0GCSqGSIb3DQEBAQUABIGAaIXuY9Wcye/P
# 0+Ovm3131xAqI6KVjJSIEifHPnG1S+/KoM3Csw1PNu7ovRhDe7y45zWj/F67ylcx
# t3BJ4yrgj4DdnpE78HFSWrmUrx4ve84TokIoKf8PR+saISou8OZb8PMGMW8zMsLN
# D2NQlPDIh4Jr4Kp/8zJ3D7L2kH6hPY0=
# SIG # End signature block
