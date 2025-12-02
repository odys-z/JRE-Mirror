import gzip
import platform
import os
import shutil
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

from typing import Callable, cast
from urllib import request

from anson.io.odysz.anson import Anson, AnsonException
from anson.io.odysz.common import LangExt
from semanticshare.io.oz.edge import JRERelease, Proxy, Temurin17Release

def guess_jretree(target_root):
    for root, dirs, _ in os.walk(target_root):
        # if "bin/java" in [os.path.join(root, d, "bin/java") for d in dirs]:
        if "bin" in dirs and "lib" in dirs and "NOTICE" in _ and "release" in _:
            return Path(root)
    return None
    # if filename.endswith(".zip") or filename.endswith(".gz"):
    #     raise RuntimeError("JRE extraction failed")

class TemurinMirror:
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
        last_ext_path = None
        for m in self.release.mirroring:
            last_ext_path = self.download_and_extract(
                            url=f'{self.release.path}/{m}',
                            target_dir=bins,
                            extract_check=extract_check, prog_hook=prog_hook)
            resolved.append(m)
        else:
            for r in resolved:
                if r not in self.release.resources:
                    self.release.resources.append(r)
        return extract_check, last_ext_path

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
                print(e, f'proxy: {proxy}')

        if extract_check:
            target_dir = Path.joinpath(target_dir, filename + '-extract')
            try: shutil.rmtree(target_dir)
            except: pass

            print(f"Extracting {filename} ...")
            if filename.endswith(".zip"):
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(target_dir)
            elif filename.endswith(".gz"):
                import tarfile
                with tarfile.open(zip_path, 'r:gz') as t:
                    t.extractall(target_dir)

            ext_root = guess_jretree(target_dir)
            if ext_root is None and (filename.endswith(".zip") or filename.endswith(".gz")):
                raise RuntimeError("JRE extraction failed")
            return ext_root

    def check_clean(self, filepath: Path):
        '''
        Verify the zip / tar.gz file is a valid package. If not, remove the file.
        :param filepath:
        :return:
        '''
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
