#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
terraform_version=$(tr -d '[:space:]' < "$repository_root/.terraform-version")
install_root=${1:-"$repository_root/.tools/terraform/$terraform_version"}
terraform_binary="$install_root/terraform"

if [ -x "$terraform_binary" ]; then
    installed_version=$("$terraform_binary" version | sed -n '1p')
    if [ "$installed_version" != "Terraform v$terraform_version" ]; then
        printf 'Cached Terraform binary has unexpected version: %s\n' "$installed_version" >&2
        exit 1
    fi
    printf '%s\n' "$terraform_binary"
    exit 0
fi

machine=$(uname -m)
case "$machine" in
    x86_64)
        terraform_arch=amd64
        expected_sha256=d25ce7b6902013ad905db3d2eab0be4cd905887fe88b81a6171b8d5503c31f3d
        ;;
    aarch64|arm64)
        terraform_arch=arm64
        expected_sha256=8891e9dcedc9e3b8950bc6af9d4d8af1f4cfade3062f53b9dc403a89f6ce8c9c
        ;;
    *)
        printf 'Unsupported Terraform authoring architecture: %s\n' "$machine" >&2
        exit 1
        ;;
esac

archive="terraform_${terraform_version}_linux_${terraform_arch}.zip"
download_url="https://releases.hashicorp.com/terraform/${terraform_version}/${archive}"
temporary_dir=$(mktemp -d)
trap 'rm -rf -- "$temporary_dir"' EXIT HUP INT TERM

curl --fail --location --silent --show-error "$download_url" --output "$temporary_dir/$archive"
printf '%s  %s\n' "$expected_sha256" "$temporary_dir/$archive" | sha256sum --check --status
unzip -q "$temporary_dir/$archive" -d "$temporary_dir/unpacked"
mkdir -p "$install_root"
install -m 0755 "$temporary_dir/unpacked/terraform" "$terraform_binary"

installed_version=$("$terraform_binary" version | sed -n '1p')
if [ "$installed_version" != "Terraform v$terraform_version" ]; then
    printf 'Installed Terraform binary has unexpected version: %s\n' "$installed_version" >&2
    exit 1
fi

printf '%s\n' "$terraform_binary"
