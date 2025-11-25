import gzip
import platform
import os
import shutil
import tarfile
import urllib.request
import zipfile
import time
from pathlib import Path

from typing import Callable, cast
from urllib import request

from anson.io.odysz.anson import Anson, AnsonException
from anson.io.odysz.common import LangExt
from semanticshare.io.oz.edge import JRERelease, Proxy, Temurin17Release


# @dataclass
# class Temurin17Release(JRERelease):
#     '''
#     Resources type of https://github.com/adoptium/temurin17-binaries
#     '''
#     date: str
#     '''
#     Mirror upating data
#     '''
#     src: str
#     path: str
#     '''
#     sub path.
#     "https://github.com/{path}/{resources[i]}" should reach the jre/jdk item.
#     "https://<mirror-ip>/deploy-path/{resources[i]}" should reach the jre/jdk item at the mirror site.
#     '''
#     resources: list[str]
#
#     mirroring: list[str]
#
#     backup: list[str]
#
#     def __init__(self):
#         super().__init__()
#         self.resources = []
#         self.mirroring = []
#         self.backup = []
#
#     def mirror(self):
#         pass
#
#     def get_resources(self):
#         pass
#
#     def set_jre(self):
#         '''
#         Find out what jre is needed, push into mirroring
#         :return: expected-itme, is-in-resources, is-in-mirroring
#         the jre item needed by current environment
#         '''
#         system = platform.system()
#         machine = platform.machine()
#
#         if system == "Windows":
#             os_name = "windows"
#             ext = "zip"
#         elif system == "Darwin":
#             os_name = "mac"
#             ext = "tar.gz"
#         elif system == "Linux":
#             os_name = "linux"
#             ext = "tar.gz"
#         else:
#             raise RuntimeError("Unsupported OS")
#
#         if machine in ("AMD64", "x86_64"):
#             arch = "x64"
#         elif machine in ("aarch64", "arm64"):
#             arch = "aarch64"
#         else:
#             raise RuntimeError(f"Unsupported arch: {machine}")
#
#
#         # build, plus = "17.0.9", "9"
#         release = "17.0.17_10"
#         zip_gz = f"OpenJDK17U-jre_{arch}_{os_name}_hotspot_{release}.{ext}"
#         # download_url = f'https://github.com/{self.path}'
#         # exp_item = f"{download_url}/jdk-{build}%2B{plus}/{zip_gz}"
#         # exp_item = f"{self.path}/{zip_gz}"
#
#         if not hasattr(self, 'mirroring') or self.mirroring is None:
#             self.mirroring = []
#         inmirror = zip_gz in self.mirroring
#         if not inmirror:
#             self.mirroring.append(zip_gz)
#         return zip_gz, zip_gz in self.resources, inmirror


class TemurinMirror():
    '''
    Thanks to Grok!
    '''

    bins = 'bins'

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
        self.check_clean(zip_path)

        if not zip_path.exists():
            print(f"Downloading JRE for {platform.system()} {platform.machine()}\n{url} ...")
            proxy = None if not hasattr(self.release, 'proxy') or LangExt.isblank(self.release.proxy) \
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
            target_dir = Path.joinpath(target_dir, filename + '-extract')
            try: shutil.rmtree(target_dir)
            except: pass

            print("Extracting...")
            if filename.endswith(".zip"):
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(target_dir)
            elif filename.endswith(".gz"):
                import tarfile
                with tarfile.open(zip_path, 'r:gz') as t:
                    t.extractall(target_dir)

            # Find the actual jre folder (Adoptium extracts to jdk-xxx-jre)
            for root, dirs, _ in os.walk(target_dir):
                #if "bin/java" in [os.path.join(root, d, "bin/java") for d in dirs]:
                if "bin" in dirs and "lib" in dirs and "NOTICE" in _ and "release" in _:
                    return Path(root)

            if filename.endswith(".zip") or filename.endswith(".gz"):
                raise RuntimeError("JRE extraction failed")

    def check_clean(self, filepath: Path):
        if filepath.suffix == ".zip":
            try:
                with zipfile.ZipFile(filepath, 'r') as zf:
                    bad_file = zf.testzip()
                    if bad_file:
                        print(f"Error: The following file in the zip is corrupt: {bad_file}")
                        return False
                    else:
                        return True
            except:
                try: os.remove(filepath) # TODO resume breakpoint
                except: pass
                return False

        elif ".tar" in filepath.suffixes and ".gz" in filepath.suffixes:
            try:
                with tarfile.open(filepath, 'r:gz') as tar:
                    tar.getmembers()
                print(f"'{filepath}' is a valid Tar Gzip file.")
            except:
                try: os.remove(filepath)
                except: pass
                return False


        elif filepath.suffix == ".gz":
            try:
                chunk_size = 1024
                if not os.path.exists(filepath):
                    print(f"Error: The file was not found. {filepath}")
                    return False

                with gzip.open(filepath, 'rb') as f:
                    while f.read(chunk_size):
                        pass
                return True
            except:
                try: os.remove(filepath)
                except: pass
                return False

        return False

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

    @classmethod
    def sync(cls, list_json):
        Anson.java_src('semanticshare')
        res = cast(Temurin17Release, Anson.from_file(list_json))
        mirror = TemurinMirror(res)
        try:
            while not mirror.lock(list_json):
                time.sleep(0.5)
            mirror.resolve_to(TemurinMirror.bins, extract_check=True)
            mirror.release.save(list_json)
        finally:
            mirror.unlock(list_json)

        return res
