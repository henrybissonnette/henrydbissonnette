import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import install_tool


class InstallNodeTests(unittest.TestCase):
    def test_amd64_uses_nodes_x64_archive_name(self):
        version = "24.13.0"
        member = f"node-v{version}-linux-x64/bin/node"
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w:xz") as archive:
            info = tarfile.TarInfo(member)
            executable = b"node"
            info.size = len(executable)
            archive.addfile(info, io.BytesIO(executable))

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "node"
            with mock.patch.object(install_tool, "download", return_value=payload.getvalue()) as download:
                install_tool.install_node(version, "amd64", destination)

            download.assert_called_once_with(
                f"https://nodejs.org/download/release/v{version}/node-v{version}-linux-x64.tar.xz",
                install_tool.NODE_SHA256["amd64"],
            )
            self.assertEqual(destination.read_bytes(), b"node")


if __name__ == "__main__":
    unittest.main()
