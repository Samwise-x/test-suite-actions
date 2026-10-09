{
  description = "Independent test-suite-actions validation tools";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/2833a4f2f08058f980a143c9fb447953ef15f1cb";
  outputs = { nixpkgs, ... }:
    let systems = [ "x86_64-linux" "aarch64-linux" ]; in {
      devShells = nixpkgs.lib.genAttrs systems (system:
        let pkgs = import nixpkgs { inherit system; }; in {
          default = pkgs.mkShell {
            packages = [ pkgs.dagger pkgs.python312 pkgs.git pkgs.gh pkgs.cosign ];
          };
        });
    };
}
