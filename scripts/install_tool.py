#!/usr/bin/env python3
"""Install a pinned authoring tool after verifying its release archive digest."""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import platform
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_SHA256 = {
    "amd64": "d25ce7b6902013ad905db3d2eab0be4cd905887fe88b81a6171b8d5503c31f3d",
    "arm64": "8891e9dcedc9e3b8950bc6af9d4d8af1f4cfade3062f53b9dc403a89f6ce8c9c",
}
NODE_SHA256 = {
    "amd64": "e798599612f4bb71333a3397ab0d095fd62214e115aea45aa858a145fc72d67e",
    "arm64": "aa881151bd0f9f154a0424dd60a72e9ce10672619121658c278a24327ef46831",
}


class InstallFailure(Exception):
    pass


def architecture() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise InstallFailure(f"unsupported Linux authoring architecture: {machine}")


def download(url: str, expected_sha256: str) -> bytes:
    digest = hashlib.sha256()
    body = io.BytesIO()
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                body.write(chunk)
    except (OSError, urllib.error.URLError) as exc:
        raise InstallFailure(f"download failed for {url}: {exc}") from exc
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise InstallFailure(f"digest mismatch for {url}: expected {expected_sha256}, got {actual}")
    return body.getvalue()


def verify_version(binary: Path, expected: str, tool: str) -> None:
    command = [str(binary), "version"] if tool == "terraform" else [str(binary), "--version"]
    try:
        first_line = subprocess.run(command, check=True, capture_output=True, text=True).stdout.splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError) as exc:
        raise InstallFailure(f"cannot execute cached {tool} binary {binary}: {exc}") from exc
    wanted = f"Terraform v{expected}" if tool == "terraform" else f"v{expected}"
    if first_line != wanted:
        raise InstallFailure(f"cached {tool} binary has version {first_line!r}; expected {wanted!r}")


def install_terraform(version: str, arch: str, destination: Path) -> None:
    archive = f"terraform_{version}_linux_{arch}.zip"
    payload = download(
        f"https://releases.hashicorp.com/terraform/{version}/{archive}",
        TERRAFORM_SHA256[arch],
    )
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as zipped:
            executable = zipped.read("terraform")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise InstallFailure(f"Terraform archive {archive} does not contain the expected executable") from exc
    destination.write_bytes(executable)


def install_node(version: str, arch: str, destination: Path) -> None:
    archive = f"node-v{version}-linux-{arch}.tar.xz"
    payload = download(
        f"https://nodejs.org/download/release/v{version}/{archive}",
        NODE_SHA256[arch],
    )
    member = f"node-v{version}-linux-{arch}/bin/node"
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:xz") as tar:
            extracted = tar.extractfile(member)
            if extracted is None:
                raise InstallFailure(f"Node archive {archive} does not contain {member}")
            executable = extracted.read()
    except (KeyError, tarfile.TarError) as exc:
        raise InstallFailure(f"Node archive {archive} does not contain the expected executable") from exc
    destination.write_bytes(executable)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=("terraform", "node"))
    args = parser.parse_args()
    tool = args.tool
    version_file = ROOT / (".terraform-version" if tool == "terraform" else ".node-version")
    version = version_file.read_text(encoding="utf-8").strip()
    cache_root = Path(os.environ.get("TOOL_CACHE_ROOT", ROOT / ".tools"))
    binary = cache_root / tool / version / tool

    try:
        if binary.is_file():
            verify_version(binary, version, tool)
        else:
            arch = architecture()
            binary.parent.mkdir(parents=True, exist_ok=True)
            temporary = binary.with_suffix(".installing")
            if tool == "terraform":
                install_terraform(version, arch, temporary)
            else:
                install_node(version, arch, temporary)
            temporary.chmod(0o755)
            os.replace(temporary, binary)
            verify_version(binary, version, tool)
    except (InstallFailure, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(binary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
