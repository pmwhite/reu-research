with import <nixpkgs> {};

let 
  req_oauth = pkgs.python35Packages.buildPythonPackage rec {
    version = "0.8.0";
    pname = "req-oauthlib";
    name = "${pname}-${version}";

    
    src = fetchurl {
      url = "http://github.com/requests/requests-oauthlib/archive/v${version}.tar.gz";
      sha256 = "18gg9dwral153c10f8bwhz2dy4nw7c6mws5a2g7gidk3z5xhqy4n";
    };

    doCheck = false;        # Internet tests fail when building in chroot
    propagatedBuildInputs = with pkgs.python35Packages; [ oauthlib requests ];
  };

  baseInputs = [ sqlite sqlitebrowser graphviz ];

in pkgs.python35Packages.buildPythonPackage rec {
  name = "reu-research";
  buildInputs = baseInputs ++ [ python35 graphviz ];

  propagatedBuildInputs = with pkgs.python35Packages; [ 
    requests_oauthlib
    pytest pyqt4 requests networkx
    matplotlib numpy pandas graphviz 
  ];
}
