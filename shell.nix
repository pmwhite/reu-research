with import <nixpkgs> {};

let vim = vim_configurable.customize {
  name = "python-vim";
  vimrcConfig.customRC = builtins.readFile ./vimrc;
  vimrcConfig.vam.knownPlugins = vimPlugins;
  vimrcConfig.vam.pluginDictionaries = [
    { names = [ "vim-nix" "ctrlp" "YouCompleteMe" ]; }
  ];
};
pycharmOrcle = idea.pycharm-community.override {
  jdk = oraclejdk8;
};
in
pkgs.python35Packages.buildPythonPackage rec {
  name = "reu-research";
  buildInputs = [ 
    vim sqlite sqlitebrowser redis pycharmOrcle graphviz ];
  propagatedBuildInputs = with pkgs.python35Packages; [ 
    pytest pyqt4 requests networkx 
    matplotlib numpy pandas graphviz ];
}
