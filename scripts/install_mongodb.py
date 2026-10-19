"""Install project-local MongoDB Community 8.0.34 from verified official archives.

Supports Windows x64 and Ubuntu 24.04 x64. No system service or administrator access required.
Other platforms can install MongoDB independently and put mongod on PATH.
"""

import hashlib
import platform
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
ARCHIVES = {
    "Windows": (
        "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.0.34.zip",
        "6b021a0864494e4decf278b36477a29eb36072432773e4e62c2f42c302630db0",
    ),
    "Linux": (
        "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2404-8.0.34.tgz",
        "3e55cdcf7013fbc805d29d8195230df4b23c7688733ee15ad58ac6bc2a416611",
    ),
}


def binary():
    name = "mongod.exe" if platform.system() == "Windows" else "mongod"
    installed = next((RUNTIME / "mongodb").glob(f"*/bin/{name}"), None)
    return installed or shutil.which("mongod")


def main():
    if binary():
        print("Native MongoDB is already available.")
        return
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit("Install MongoDB for your architecture and add mongod to PATH.")
    system = platform.system()
    if system not in ARCHIVES:
        raise SystemExit("Install MongoDB for your OS and add mongod to PATH.")
    if system == "Linux" and not (
        "Ubuntu" in Path("/etc/os-release").read_text()
        and "24.04" in Path("/etc/os-release").read_text()
    ):
        raise SystemExit(
            "This installer targets Ubuntu 24.04; install MongoDB for your distribution."
        )
    url, expected = ARCHIVES[system]
    RUNTIME.mkdir(exist_ok=True)
    archive = RUNTIME / url.rsplit("/", 1)[-1]
    if not archive.exists():
        print("Downloading native MongoDB Community 8.0.34 from mongodb.org…", flush=True)
        urllib.request.urlretrieve(url, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise SystemExit("MongoDB archive checksum mismatch. Remove the archive and retry.")
    destination = RUNTIME / "mongodb"
    if system == "Windows":
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(destination)
    else:
        with tarfile.open(archive) as handle:
            handle.extractall(destination, filter="data")
    if not binary():
        raise SystemExit("Archive extracted, but mongod was not found.")
    print("Native MongoDB installed; SHA-256 matches the official release manifest.")


if __name__ == "__main__":
    main()
