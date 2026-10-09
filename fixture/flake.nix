{
  description = "Isolated OpenCode Actions fixture validation";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/2833a4f2f08058f980a143c9fb447953ef15f1cb";
  inputs.dagger.url = "github:dagger/nix/21ee7262e0ccfffba6bd43c9044fb4c5c8db2d91";
  inputs.dagger.inputs.nixpkgs.follows = "nixpkgs";
  outputs = { nixpkgs, dagger, ... }:
    let systems = [ "x86_64-linux" "aarch64-linux" ]; in {
      devShells = nixpkgs.lib.genAttrs systems (system:
        let pkgs = import nixpkgs { inherit system; }; in {
          default = pkgs.mkShell { packages = [ dagger.packages.${system}.dagger pkgs.python312 ]; };
        });
    };
}
