{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      shortRev = with self; if sourceInfo?dirtyShortRev then sourceInfo.dirtyShortRev else sourceInfo.shortRev;
      pkgs = forAllSystems (system: nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (system: {
        default = pkgs.${system}.stdenv.mkDerivation {
          name = "ble-scale";
          version = shortRev;
          dontUnpack = true;
          buildInputs = with pkgs.${system}; [
            (python313.withPackages (pythonPackages: with pythonPackages; [
              bleak
              requests
              plotext
            ]))
          ];
          installPhase = ''
            install -Dm755 ${./ble-scale.py} $out/bin/ble-scale
            install -Dm755 ${./scale-graph.py} $out/bin/scale-graph
          '';
        };
      });

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/ble-scale";
        };

        graph = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/scale-graph";
        };
      });

      devShells = forAllSystems (system: {
        default = pkgs.${system}.mkShell {
          buildInputs = with pkgs.${system}; [
            sqlite
            python313
            python313Packages.bleak
            python313Packages.requests
            python313Packages.plotext
          ];
        };
      });
    };
}
