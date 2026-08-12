#!/usr/bin/env python3
"""Install the exact AWS CLI v2 used by the credentialed workflow job."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / ".aws-cli-version").read_text(encoding="utf-8").strip()
ARCHIVE_SHA256 = "b665b24dae1ed70bc38ef03998570307a0363839196b564bf04f8d7502132b9a"


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if root not in target.parents and target != root:
            raise ValueError("AWS CLI archive contains an escaping path")
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError("AWS CLI archive contains an unsupported symbolic link")
        archive.extract(member, destination)
        permissions = stat.S_IMODE(mode)
        if permissions and target.exists():
            target.chmod(permissions)


def download(destination: Path) -> None:
    url = f"https://awscli.amazonaws.com/awscli-exe-linux-x86_64-{VERSION}.zip"
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError("pinned AWS CLI download failed") from exc
    if digest.hexdigest() != ARCHIVE_SHA256:
        raise RuntimeError("pinned AWS CLI archive digest mismatch")


def verify(binary: Path) -> None:
    completed = subprocess.run([str(binary), "--version"], capture_output=True, text=True, check=True)
    version_line = (completed.stdout or completed.stderr).strip()
    if not version_line.startswith(f"aws-cli/{VERSION} "):
        raise RuntimeError("installed AWS CLI version does not match .aws-cli-version")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-root", type=Path, required=True)
    parser.add_argument("--bin-dir", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        print("ERROR: pinned AWS CLI workflow tool supports the GitHub Linux x64 runner only", file=sys.stderr)
        return 1
    install_root = args.install_root.resolve()
    bin_dir = args.bin_dir.resolve()
    binary = bin_dir / "aws"
    try:
        if binary.is_file():
            verify(binary)
        else:
            work = install_root.with_name(f"{install_root.name}.staging")
            if work.exists():
                shutil.rmtree(work)
            work.mkdir(parents=True, mode=0o700)
            archive_path = work / "awscliv2.zip"
            download(archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                safe_extract(archive, work)
            bin_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    str(work / "aws/install"),
                    "--install-dir",
                    str(install_root),
                    "--bin-dir",
                    str(bin_dir),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            shutil.rmtree(work)
            verify(binary)
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError, zipfile.BadZipFile) as exc:
        print(f"ERROR: AWS CLI installation failed safely: {type(exc).__name__}", file=sys.stderr)
        return 1
    os.chmod(binary, 0o755)
    print("Pinned AWS CLI installed and version-verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
