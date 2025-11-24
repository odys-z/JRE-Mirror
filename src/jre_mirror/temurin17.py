import platform
import urllib.request
import zipfile
import os
from pathlib import Path

from dataclasses import dataclass
from typing import Callable, cast
from urllib import request
from urllib.parse import ParseResult

from anson.io.odysz.anson import Anson, AnsonException
from anson.io.odysz.common import LangExt
from semanticshare.io.oz.invoke import JRERelease, Proxy
from urllib3 import proxy_from_url


@dataclass
class Temurin17Release(JRERelease):
    '''
    Resources type of https://github.com/adoptium/temurin17-binaries
    '''
    date: str
    '''
    Mirror upating data
    '''
    src: str
    path: str
    '''
    sub path.
    "https://github.com/{path}/{resources[i]}" should reach the jre/jdk item.
    "https://<mirror-ip>/deploy-path/{resources[i]}" should reach the jre/jdk item at the mirror site.
    '''
    resources: list[str]

    mirroring: list[str]

    proxy: str

    def __init__(self):
        super().__init__()

    def mirror(self):
        pass

    def get_resources(self):
        pass

    def jre(self):
        '''
        :return: expected-itme, existing-flag, synchronize-flag (wait | done | NA)
        the jre item needed by current environment
        '''
        system = platform.system()
        machine = platform.machine()

        if system == "Windows":
            os_name = "windows"
            ext = "zip"
        elif system == "Darwin":
            os_name = "mac"
            ext = "tar.gz"
        elif system == "Linux":
            os_name = "linux"
            ext = "tar.gz"
        else:
            raise RuntimeError("Unsupported OS")

        if machine in ("AMD64", "x86_64"):
            arch = "x64"
        elif machine in ("aarch64", "arm64"):
            arch = "aarch64"
        else:
            raise RuntimeError(f"Unsupported arch: {machine}")

        download_url = f'https://github.com/{self.path}'

        build, plus = "17.0.9", "9"
        zip_gz = f"OpenJDK17U-jre_{arch}_{os_name}_hotspot_{build}_{plus}.{ext}"
        exp_item = f"{download_url}/jdk-{build}%2B{plus}/{zip_gz}"
        exists = exp_item in self.resources
        wait = False if exists else f'wait:{exp_item}' in self.resources
        return exp_item, exists, wait


class TemurinMirror():
    '''
    Thanks to Grok!
    '''

    release: Temurin17Release

    def __init__(self, release: JRERelease):
        self.release = cast(Temurin17Release, release)

    def resolve_to(self, bins: str,
                extract_check: bool = False,
                prog_hook: Callable[[int, int, int], None] = None):
        resolved = []
        for m in self.release.mirroring:
            self.download_and_extract(url=f'{self.release.path}/{m}',
                        target_dir=bins, extract_check=extract_check, prog_hook=prog_hook)
            resolved.append(m)
        else:
            for r in resolved:
                if r not in self.release.resources:
                    self.release.resources.append(r)

    def download_and_extract(self, url: str,
                             target_dir: str="jre-download",
                             extract_check: bool=False,
                             prog_hook: Callable[[int, int, int], None]=None):

        def progress_hook(blocknum, blocksize, totalsize):
            read = blocknum * blocksize
            if totalsize > 0:
                percent = min(100, read * 100 // totalsize)
                print(f"\rDownloading... {percent}%", end="")

        target_dir = Path(target_dir)
        target_dir.mkdir(exist_ok=True)

        filename = url.split("/")[-1]
        zip_path = target_dir / filename

        if not zip_path.exists():
            print(f"Downloading JRE for {platform.system()} {platform.machine()}\n{url} ...")
            proxy = None if LangExt.isblank(self.release.proxy) \
                    else cast(Proxy, Anson.from_file(self.release.proxy))
            try:
                # TODO support breakpoints
                if proxy is not None:
                    proxy_handler = request.ProxyHandler({'http': proxy.http, 'https': proxy.https})
                    opener = urllib.request.build_opener(proxy_handler)
                    request.install_opener(opener)

                request.urlretrieve(url, zip_path,
                           reporthook=progress_hook if prog_hook is None else prog_hook)

            except IOError as e:
                print(e)

        if extract_check:
            print("Extracting...")
            if filename.endswith(".zip"):
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(target_dir)
            else:
                import tarfile
                with tarfile.open(zip_path, 'r:gz') as t:
                    t.extractall(target_dir)

            # Find the actual jre folder (Adoptium extracts to jdk-xxx-jre)
            for root, dirs, _ in os.walk(target_dir):
                #if "bin/java" in [os.path.join(root, d, "bin/java") for d in dirs]:
                if "bin" in dirs and "lib" in dirs and "NOTICE" in _ and "release" in _:
                    return Path(root)
            raise RuntimeError("JRE extraction failed")

    def lock(self, list_json):
        if not LangExt.isblank(list_json):
            if not LangExt.suffix(list_json, '.lock'):
                _lock_file = f'{list_json}.lock'
                if not os.path.exists(_lock_file):
                    with open(_lock_file, 'w') as f:
                        pass
                    return True
                else: return False
        raise AnsonException(0, 'Locking {} failed.', list_json)

    def unlock(self, list_json):
        if not LangExt.suffix(list_json, '.lock') and os.path.exists(f'{list_json}.lock'):
            try: os.remove(f'{list_json}.lock')
            except: pass
