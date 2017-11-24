"""" EDITING CONFIG

" For the most part, I operate with spaces in ts=4, I use editorconfig
" and autocmds to enforce tabs for C++, go etc.
"
set ts=4 sw=4 ai smarttab smartindent expandtab backspace=2
set encoding=utf-8

" Enable file-type recognition and syntax highlighting.
"
filetype on
filetype plugin on
filetype indent on
syntax on

" Enable the wild-card menu when trying to find files.
"
set wildmenu

"""" KEY MAPS

" I like '[' mapped to 'next warning/error/grep result', so
" I can skip thru search results or compile errors quickly.
"
nnoremap [ :cn<CR>

"""" DISPLAY

" Limiting stuff to 80 characters makes for easier mobile viewing and
" side-by-side, esp 3-way, compares.
"
set colorcolumn=81

set background=dark 

set lazyredraw modeline modelines=1 showtabline=1 laststatus=2

" Powerline config stuff.
"
let powerline_root=$POWERLINE_ROOT
if powerline_root != ""
	set rtp+=$POWERLINE_ROOT/powerline/bindings/vim
	if has('macunix')
		set guifont=Inconsolata\ for\ Powerline:h14
	endif
	let g:Powerline_symbols = 'fancy'
	set fillchars+=stl:\ ,stlnc:\ 
	set t_Co=256
	if has('unix')
		set term=xterm-256color
		set termencoding=utf-8
	endif
endif

"""" FILE TYPE CONFIG

augroup configgroup
	autocmd!
	" remove trailing spaces
	autocmd FileType c,cpp,python,*.sh,.vimrc,.bashrc,*.xml,shell,html,go,txt,json,yaml,md autocmd BufWritePre <buffer> %s/\s\+$//e

	" tabs vs spaces
	autocmd FileType python                setlocal expandtab number colorcolumn=80 colorcolumn=120
	autocmd FileType *.sh,.vimrc,.bashrc   setlocal expandtab number colorcolumn=80 colorcolumn=120 ts=2 sw=2
	autocmd FileType *.cpp,*.h,*.java,*.go setlocal noexpandtab number colorcolumn=120 ts=4 sw=4
augroup END

