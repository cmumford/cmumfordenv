cmumfordenv
===========

This repository contains the standard parts of my home user environment. I go back and forth between many computers, at home and work, and use Linux/Mac/Windows. This project helps me keep all of my machines in sync, and to have tools that (hopefully) work on all platforms for my common tasks.

Configuration Files
-------------------------
These are my configuration files (.zshrc, .bashrc, .vimrc, etc.)

I've tried to keep the shell configurations such that I could use either [Bash](http://www.gnu.org/software/bash/bash.html) or [Zsh](http://www.zsh.org/) interchangeably.
I'm not a super shell stud so don't trust my configuration too much, but it seems to work for me.
I'm mostly a Zsh guy so the Bash configuration may have bit rotted just a bit - but not too much.

    cd
    git clone url cmumford

## Windows Installation

**In an elevated command prompt**
**Note**: mklink requires elevated privileges.

    mklink /J "%USERPROFILE%\.vim" "%USERPROFILE%"\cmumford\home\.vim
    mklink _vimrc cmumford\home\.vimrc
    mklink .gitconfig cmumford\home\.gitconfig
    mklink /J "%USERPROFILE%\Documents\WindowsPowerShell" cmumford\WindowsPowerShell

**In a standard command prompt**

    git clone https://github.com/VundleVim/Vundle.vim.git .vim/bundle/Vundle.vim
    echo "" > .vimrc_work

Download ctags, and put it in your path (cmumford/bin).

## Installing Vundle Plugins

The first time you run Vim you will need to install it's plugins. Start Vim and type:

    :PluginInstall

Utilities
-------------------------
<dl>
  <dt>vmod</dt>
  <dd>Open up (in <a href="http://www.vim.org/">vim</a>) all locally modified file(s) in a <a href="http://git-scm.com/">Git</a> project's branch. Can also open <b>all</b> files modified in the current branch.</dd>
  <dt>git-rebaseall</dt>
  <dd>Rebase all local Git branches onto their parent.</dd>
</dl>

**Note**: All (hopefully) of my utilities support the --help command line argument, so use that to get more information on what they do and how to run them.

There are other small utilities there, but nothing of significance.

That's about it. Nothing super cool.

