{ pkgs }: {
  deps = [
    # Python 3.11
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv
    
    # Node.js 20
    pkgs.nodejs_20
    pkgs.nodePackages.npm
    
    # 빌드 도구
    pkgs.gcc
    pkgs.gnumake
    pkgs.libffi
    pkgs.openssl
    pkgs.zlib
    
    # SQLite
    pkgs.sqlite
    
    # 기타 유틸리티
    pkgs.bash
    pkgs.coreutils
  ];
  
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.libffi
      pkgs.openssl
      pkgs.zlib
    ];
    LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.libffi
      pkgs.openssl
      pkgs.zlib
    ];
  };
}

