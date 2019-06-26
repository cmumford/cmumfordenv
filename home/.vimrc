source $VIMRUNTIME/vimrc_example.vim
source $VIMRUNTIME/mswin.vim
behave mswin

if has('win32') || has('win64')
    set runtimepath=$USERPROFILE\.vim,$VIM/vimfiles,$VIMRUNTIME,$VIM/vimfiles/after,$USERPROFILE\.vim/after
endif

syntax enable

let $PAGER=''

" Highlight search
set hlsearch

" While typing a search jump to matches
set incsearch

" tab spaces
set tabstop=2
set sw=2
set sts=2
set expandtab
set smarttab

" Don't create the backup files
set nobackup

" Don't create undo files.
set noundofile

" Automatically write file before making
set autowrite

" Default window width and height
if has("gui_running")
    " Text width
    set tw=132
    set columns=120
    set lines=56
endif

" Show line numbers
set number

set nowrap

set autoindent
set smartindent

" Search for tags file recursively in parent directories
set tags+=tags;/

if has("win32") || has("win16")
  set tags+=~/vimfiles/tags/python.ctags
  set shell=cmd.exe
  set rtp+=~/.vim/bundle/Vundle.vim
else
  set tags+=~/.vim/tags/python.ctags
  set shell=/bin/zsh
  set rtp+=~/.vim/bundle/Vundle.vim
endif


" See http://www.8t8.us/vim/vim.html
set autochdir

" Move between files in a long list
map <F2> \be
map <F3> :prev<cr>
map <F4> :next<cr>
map <F6> :b#<CR>
nnoremap <silent> <F3> :TlistToggle<CR>
nnoremap <silent> <F9> :NERDTreeToggle<CR>
let Tlist_Exit_OnlyWindow = 1     " exit if taglist is last window open
let Tlist_Show_One_File = 1       " Only show tags for current buffer
let Tlist_Enable_Fold_Column = 0  " no fold column (only showing one file)
let tlist_sql_settings = 'sql;P:package;t:table'
let tlist_ant_settings = 'ant;p:Project;r:Property;t:Target'

nmap <silent> <F5> :FSHere<cr>

" Required by Project plugin
set nocompatible

" Required for chromium/vim-codesearch plugin.
set hidden

set nocp
" https://github.com/gmarik/vundle#readme
" git clone https://github.com/gmarik/vundle.git ~/.vim/bundle/vundle
" For Windows see https://github.com/gmarik/vundle/wiki/Vundle-for-Windows
filetype off  " Required!
set rtp+=~/.fzf
call vundle#begin()

" let Vundle manage Vundle, required
Plugin 'VundleVim/Vundle.vim'
" https://github.com/chromium/vim-codesearch
Plugin 'chromium/vim-codesearch'
Plugin 'corntrace/bufexplorer'
Plugin 'junegunn/fzf.vim'
Plugin 'fatih/vim-go'
Plugin 'fs111/pydoc.vim'
Plugin 'FSwitch'
Plugin 'grep.vim'
Plugin 'info.vim'
Plugin 'mileszs/ack.vim'
Plugin 'screen.vim'
Plugin 'scrooloose/nerdtree'
Plugin 'scrooloose/syntastic'
Plugin 'taglist.vim'
Plugin 'tmhedberg/matchit'
Plugin 'tpope/vim-dispatch'
Plugin 'tpope/vim-fugitive'
Plugin 'tpope/vim-unimpaired'
Plugin 'Wombat'
call vundle#end()            " required

filetype plugin indent on

if has("gui_running")
    colorscheme wombat
"    set noantialias
endif

let g:load_doxygen_syntax=1

set exrc    " enable per-directory .vimrc files
set secure  " disable unsafe commands in local .vimrc files

" Omnicomplete
autocmd FileType python set omnifunc=pythoncomplete#Complete
autocmd FileType javascript set omnifunc=javascriptcomplete#CompleteJS
autocmd FileType html set omnifunc=htmlcomplete#CompleteTags
autocmd FileType css set omnifunc=csscomplete#CompleteCSS
autocmd FileType xml set omnifunc=xmlcomplete#CompleteTags
autocmd FileType php set omnifunc=phpcomplete#CompletePHP
autocmd FileType c set omnifunc=ccomplete#Complete
autocmd FileType make setlocal noexpandtab

" ack.vim's defaults use '-s' which doesn't exist on ack-grep with Ubuntu 12.04
let g:ack_default_options = " --sort-files --with-filename --nocolor --nogroup --column"

"Show in a new window the Subversion blame annotation for the current file.
" Problem: when there are local mods this doesn't align with the source file.
" To do: When invoked on a revnum in a Blame window, re-blame same file up to previous rev.
:function s:svnBlame()
   let line = line(".")
   setlocal nowrap
   aboveleft 18vnew
   setlocal nomodified readonly buftype=nofile nowrap winwidth=1
"   NoSpaceHi
   " blame, ignoring white space changes
   %!svn blame --force --extensions --ignore-all-space "#"
   " find the highest revision number and highlight it
   "%!sort -n
   "normal G*u
   " return to original line
   exec "normal " . line . "G"
   setlocal scrollbind
   wincmd p
   setlocal scrollbind
   setlocal nonumber
   syncbind
:endfunction
:map gb :call <SID>svnBlame()<CR>
:command Blame call s:svnBlame()

au BufNewFile,BufRead Makefile.inc set filetype=make
au BufNewFile,BufRead Makefile.Ubuntu set filetype=make
au BufNewFile,BufRead Makefile.Ubuntu.Release set filetype=make
au BufNewFile,BufRead Makefile.v8.inc set filetype=make

" custom commands to easily navigate around the source code
:function g:GotoDir(shortcut)
  let dir = system("python ${HOME}/bin/go.py " . a:shortcut)
  execute "cd " . expand(dir)
  pwd
:endfunction
:command -nargs=1 G call g:GotoDir("<args>")

" For tab completion at bottom of screen (like for tabs)
set wildmenu
set wildmode=list:longest,full

" For python syntax checking.
autocmd BufRead *.py set makeprg=python\ -c\ \"import\ py_compile,sys;\ sys.stderr=sys.stdout;\ py_compile.compile(r'%')\" 
autocmd BufRead *.py set efm=%C\ %.%#,%A\ \ File\ \"%f\"\\,\ line\ %l%.%#,%Z%[%^\ ]%\\@=%m

" Automatically indent the next line after these keywords
autocmd BufRead *.py set smartindent cinwords=if,elif,else,for,while,try,except,finally,def,class

" Remove all trailing spaces during exit
autocmd BufWritePre *.py :%s/\s\+$//e

" To move between tabs using Alt+<Left Arrow> or Alt+<Right Arrow>
map <silent><A-Right> :tabnext<CR>
map <silent><A-Left> :tabprevious<CR>


if version >= 700
   set spell
   highlight clear SpellBad
   highlight SpellBad term=standout ctermfg=3 term=underline cterm=underline
   highlight clear SpellCap
   highlight SpellCap term=underline cterm=underline
   highlight clear SpellRare
   highlight SpellRare term=underline cterm=underline
   highlight clear SpellLocal
   highlight SpellLocal term=underline cterm=underline
endif

" To make vimdiff more readable
highlight DiffAdd term=reverse cterm=bold ctermbg=green ctermfg=black
highlight DiffChange term=reverse cterm=bold ctermbg=cyan ctermfg=black
highlight DiffText term=reverse cterm=bold ctermbg=gray ctermfg=black
highlight DiffDelete term=reverse cterm=bold ctermbg=red ctermfg=black

if has("gui_running")
    set background=dark
endif

if has("gui_macvim")
  set guifont=Consolas:h14
  if &background == "dark"
    set transparency=8
  endif
elseif has("gui_win32") || has("gui_win16")
  set guifont=Consolas:h11
elseif has("gui_running")
  set guifont=Monospace\ 11
endif

" Match whitespace except when typing at end of line
highlight ExtraWhitespace ctermbg=darkgreen guibg=lightgreen
match ExtraWhitespace /\s\+\%#\@<!$/
au InsertEnter * match ExtraWhitespace /\s\+\%#\@<!$/
au InsertLeave * match ExtraWhitespace /\s\+$/

" A vertical line at 80 columns
au FileType python,c,cpp set colorcolumn=80
au BufWinLeave * set colorcolumn=0

set bg=dark

let NERDTreeIgnore = ['\.pyc$']

" fugitive-vim stuff
" Auto-clean fugitive buffers
autocmd BufReadPost fugitive://* set bufhidden=delete
" Show current branch in the status line
set statusline=%<%f\ %h%m%r%{fugitive#statusline()}%=%-14.(%l,%c%V%)\ %P

" custom commands to easily navigate around the source code
:function g:EditProjectFile(file, projAlias)
  let @d = system("python ${HOME}/bin/go.py " . a:projAlias)
  let dir = substitute(@d,"[\n\r]$","","g")
  let lTrimmedFile = substitute(a:file,"^[│/\.]*","","g")
  let trimmedFile = substitute(lTrimmedFile, "[0-9:]*$","","g")
  let path = expand(dir) . "/" . trimmedFile
  exec ":e ".expand(path)
:endfunction
:command -nargs=1 NN call g:EditProjectFile("<args>", "c")
:command -nargs=1 BB call g:EditProjectFile("<args>", "b")

" Used by FSwitch - probably a better way to do this.
au! BufEnter *.cpp let b:fswitchdst = 'hpp,h' | let b:fswitchlocs = '.'
au! BufEnter *.c let b:fswitchdst = 'hpp,h' | let b:fswitchlocs = '.'
au! BufEnter *.cc let b:fswitchdst = 'hpp,h' | let b:fswitchlocs = '.'
au! BufEnter *.h let b:fswitchdst = 'cc,cpp,c' | let b:fswitchlocs = '.'

set nofoldenable    " disable folding

" file is large from 10mb
let g:LargeFile = 1024 * 1024 * 10
augroup LargeFile
 autocmd BufReadPre * let f=getfsize(expand("<afile>")) | if f > g:LargeFile || f == -2 | call LargeFile() | endif
augroup END

function LargeFile()
 " no syntax highlighting etc
 set eventignore+=FileType
 " save memory when other file is viewed
 setlocal bufhidden=unload
 " is read-only (write with :w new_filename)
 setlocal buftype=nowrite
 " no undo possible
 setlocal undolevels=-1
 " display message
 autocmd VimEnter *  echo "The file is larger than " . (g:LargeFile / 1024 / 1024) . " MB, so some options are changed (see .vimrc for details)."
endfunction

source ~/.vimrc_work

if has("gui_running")
  highlight Cursor guifg=black guibg=cyan
  highlight iCursor guifg=red guibg=green
  set guicursor=n-v-c:block-Cursor
  set guicursor+=i:ver100-iCursor
  set guicursor+=n-v-c:blinkon0
  set guicursor+=i:blinkwait10
endif
