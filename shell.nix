with import <nixpkgs> {};

let vim = vim_configurable.customize {
  name = "python-vim";
  vimrcConfig.customRC = builtins.readFile ./vimrc;
  vimrcConfig.vam.knownPlugins = vimPlugins;
  vimrcConfig.vam.pluginDictionaries = [
    { names = [ "vim-nix" "ctrlp" "YouCompleteMe" "easymotion" "colorsamplerpack" "airline" "gitgutter" ]; }
  ];
};
pycharmOrcle = idea.pycharm-community.override {
  jdk = oraclejdk8;
};

requests-oauth = pkgs.python35Packages.buildPythonPackage rec {
  name = "requests-oauthlib";

  src = fetchurl {
    url = "http://github.com/requests/requests-oauthlib/archive/v0.8.0.tar.gz";
    sha256 = "18gg9dwral153c10f8bwhz2dy4nw7c6mws5a2g7gidk3z5xhqy4n";
  };

  doCheck = false;        # Internet tests fail when building in chroot
  propagatedBuildInputs = with pkgs.python35Packages; [ oauthlib requests ];
};

python-twitter = pkgs.python35Packages.buildPythonPackage {
  name = "python-twitter";

  src = fetchurl {
    url = "https://github.com/bear/python-twitter/archive/v3.3.tar.gz";
    sha256 = "18ychdm4wd6wa8jb97gvsqcfbnx0gfvk5hvhknld34qfpfmgjkxk";
  };
  
  doCheck = false;
  propagatedBuildInputs = with pkgs.python35Packages; [ 
    future requests requests-oauth ];

};

in
pkgs.python35Packages.buildPythonPackage rec {
  name = "reu-research";
  buildInputs = [ 
    vim sqlite sqlitebrowser redis pycharmOrcle python35 graphviz inkscape ];
  propagatedBuildInputs = with pkgs.python35Packages; [ 
    pytest pyqt4 requests networkx 
    matplotlib numpy pandas graphviz python-twitter ];
}
