with import <nixpkgs> {};
with pkgs.python35Packages;

let vim = vim_configurable.customize {
  name = "python-vim";
  vimrcConfig.customRC = builtins.readFile ./vimrc;
  vimrcConfig.vam.knownPlugins = vimPlugins;
  vimrcConfig.vam.pluginDictionaries = [
    { names = [ "vim-nix" "ctrlp" "YouCompleteMe" ]; }
  ];
};
in
buildPythonPackage rec {
  name = "reu-research";
  buildInputs = [ vim sqlite sqlitebrowser ];
  propagatedBuildInputs = [ pytest requests networkx matplotlib ];
}
