{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/packages/
  packages = [
    pkgs.git
    pkgs.postgresql_16
  ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    version = "3.12";
    # poetry = {
    #   enable = true;
    #   activate.enable = true;
    #   install = {
    #     enable = true;
    #     allExtras = true;
    #     compile = true;
    #     quiet = false;
    #   };
    # };
  };

  dotenv.enable = true;

  # https://devenv.sh/processes/
  # example: processes.cargo-watch.exec = "cargo-watch";

  # Enable PostgreSQL service
  #   services.postgres = {
  #     enable = true; # to delete: set to false, then rm .devenv/state/postgres
  #     port = 5444;
  #     listen_addresses = "127.0.0.1";
  #     initialScript = "
  # CREATE USER postgres SUPERUSER;
  # ALTER USER postgres WITH PASSWORD 'mysecretpassword';
  # CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
  #     ";
  #     settings.shared_preload_libraries = "pg_stat_statements";
  #   };

  # Auto-start development environment
  enterShell = ''
    echo "Crystal DBA Agent Client Development Environment"
  '';

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';

  # See full reference at https://devenv.sh/reference/options/
}
