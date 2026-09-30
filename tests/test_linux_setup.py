import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from linux_vite_lab import extract_archive


class LinuxSetupTests(unittest.TestCase):
    def test_old_python_extraction_supports_regular_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "runtime.tar"
            with tarfile.open(archive, "w") as target:
                info = tarfile.TarInfo("runtime/bin/node")
                info.size = 4
                target.addfile(info, io.BytesIO(b"node"))
            destination = root / "unpacked"
            destination.mkdir()
            with patch("linux_vite_lab.inspect.signature", return_value=type("Signature", (), {"parameters": {}})()):
                extract_archive(archive, destination)
            self.assertEqual((destination / "runtime/bin/node").read_bytes(), b"node")

    def test_archive_member_and_link_escapes_are_rejected(self):
        for is_link in (False, True):
            with self.subTest(link=is_link), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root / "runtime.tar"
                with tarfile.open(archive, "w") as target:
                    info = tarfile.TarInfo("runtime/link" if is_link else "../outside")
                    if is_link:
                        info.type = tarfile.SYMTYPE
                        info.linkname = "../../outside"
                    target.addfile(info)
                destination = root / "unpacked"
                destination.mkdir()
                with self.assertRaises(ValueError):
                    extract_archive(archive, destination)
                self.assertFalse((root / "outside").exists())
