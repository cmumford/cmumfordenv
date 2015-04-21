$ErrorActionPreference = "Stop"

function UpdateGclient {
  Write-Host "Updating depot tools..."
  gclient --version
  gclient --version
}

function UpdateProject([string] $dir) {
  Write-Host "Updating:"$dir
  cd $dir
  git fetch origin
  if ($LastExitCode -ne 0) {
    $host.ui.WriteErrorLine("Error fetching from origin.")
    exit $LastExitCode
  }
  git rebaseall
  if ($LastExitCode -ne 0) {
    $host.ui.WriteErrorLine("Error Rebasing - probably a conflict?")
    exit $LastExitCode
  }
  git checkout master
  if ($LastExitCode -ne 0) {
    $host.ui.WriteErrorLine("Error checking out master branch.")
    exit $LastExitCode
  }
}

function GclientSync([string] $topdir) {
  Write-Host "Syncing gclient in:"$topdir
  cd $topdir
  gclient sync
  if ($LastExitCode -ne 0) {
    $host.ui.WriteErrorLine("Error running gclient sync.")
    exit $LastExitCode
  }
}

function UpdateChrome {
  $topdir = "D:\"
  $srcdir = "${topdir}src"
  UpdateProject("$srcdir\third_party\WebKit")
  UpdateProject($srcdir)
  GClientSync($topdir)
}

UpdateGclient
UpdateChrome
