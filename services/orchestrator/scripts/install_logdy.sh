#!/bin/sh

version='v0.17.0'

os=$(uname -s | tr '[:upper:]' '[:lower:]')
machine=$(uname -m)

case $os in
linux | darwin)
  ext=''
  ;;
windows)
  os=windows
  ext='.exe'
  ;;
*)
  echo "Unsupported OS: $os" >&2
  exit 1
  ;;
esac

case $machine in
x86_64 | amd64)
  arch=amd64
  ;;
arm64 | aarch64)
  arch=arm64
  ;;
*)
  echo "Unsupported architecture: $machine" >&2
  exit 1
  ;;
esac

asset="logdy_${os}_${arch}${ext}"
echo "Installing Logdy.dev ${version} (${asset})"
curl -Lfs "https://github.com/logdyhq/logdy-core/releases/download/${version}/${asset}" -o logdy

chmod +x logdy
mv logdy .venv/bin/logdy
# mv logdy /usr/local/bin/logdy
