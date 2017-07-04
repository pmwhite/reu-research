set nocompatible

" Turn on nice things
filetype on
filetype plugin indent on
syntax on

"" Appearance
colorscheme molokai

" Gvim settings
set guioptions-=T
set guioptions-=r
set guioptions-=L
set guifont=consolas:h11:cANSI

" Line numbers
set number
set relativenumber

" Indentation and tab settings
set expandtab
set shiftround
set tabstop=2
set shiftwidth=2
set autoindent

" Status line
set laststatus=2
set statusline=%.40F%h%m%r%y%=%c%l/%L\ %P

"" Keybindings
nnoremap ; :
nnoremap : ;
inoremap jk <esc>

" Backspace everything
set backspace=indent,eol,start

" Mouse support
set mouse=a
