with import <nixpkgs> {};

let 
  vim = vim_configurable.customize {
    name = "med";
    vimrcConfig.customRC = builtins.readFile ./vimrc;
    vimrcConfig.vam.knownPlugins = vimPlugins;
    vimrcConfig.vam.pluginDictionaries = [
      { 
        names = [ 
          "vim-nix" "ctrlp" "YouCompleteMe" "easymotion" 
          "colorsamplerpack" "airline" "gitgutter" 
        ]; 
      }
    ];
  };

  pycharmOrcle = idea.pycharm-community.override {
    jdk = oraclejdk8;
  };

  baseInputs = [ vim sqlite sqlitebrowser graphviz ];

  ocamlVersion = (builtins.parseDrvName ocamlPackages.ocaml.name).version;
  findlibSiteLib = "${ocamlPackages.findlib}/lib/ocaml/${ocamlVersion}/site-lib";

in {
  pyshell = pkgs.python35Packages.buildPythonPackage rec {
    name = "reu-research";
    buildInputs = baseInputs ++ [ pycharmOrcle python35 graphviz ];

    propagatedBuildInputs = with pkgs.python35Packages; [ 
      pytest pyqt4 requests networkx sqlalchemy
      matplotlib numpy pandas graphviz 
    ];
  };

  mlshell = stdenv.mkDerivation {
    name = "reu-research";

    buildInputs = with ocamlPackages; baseInputs ++ [
      ocaml camlp4 utop ocamlbuild ocamlgraph core 
      findlib ocpIndent yojson
    ];

    findlib = findlibSiteLib;
  };
}
