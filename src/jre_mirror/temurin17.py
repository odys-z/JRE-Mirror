import gzip
import platform
import os
import shutil
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

from typing import Callable, cast, Union, Optional
from urllib import request

from anson.io.odysz.anson import Anson, AnsonException
from anson.io.odysz.common import LangExt, check_package
from semanticshare.io.oz.edge import JRERelease, Proxy, Temurin17Release, extract_check_jretree

"""
def guess_jretree(target_root):
    '''
    Find java bin in target root. (only verified against JRE 17 tree)
    :param target_root:
    :return: root path of the extracted JRE tree, or None if not found.
    '''
    for root, dirs, _ in os.walk(target_root):
        if "bin" in dirs and "lib" in dirs and "NOTICE" in _ and "release" in _:
            return Path(root)
    return None
"""

class TemurinMirror:
    bins = 'bins'

    release: Temurin17Release

    def __init__(self, release: JRERelease):
        self.release = cast(Temurin17Release, release)

    def resolve_to(self, bins: str,
                extract_check: bool = False,
                prog_hook: Optional[Callable[[int, int, Union[int, float]], None]] = None):
        '''
        resolve the mirroring resources to the target directory, downloading and extracting as needed.
        :param bins: target directory to place the resolved resources.
        :param extract_check: if True, will extract the downloaded resources and check for a valid JRE tree.
        :param prog_hook: optional progress hook for download progress reporting.
        :return: a tuple of (extract_check, last_ext_path) where last_ext_path is the path to the last extracted JRE tree, or None if no extraction was performed.
        '''
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
                             prog_hook: Optional[Callable[[int, int, float], None]]=None):

        start_time = time.monotonic()
        last_print = [0.0]  # mutable closure cell
        def progress_hook(blocknum: int, blocksize: int, totalsize: float):
            now = time.monotonic()
            # throttle: only print every 0.5s OR on the final block, to avoid spamming
            read:float = blocknum * blocksize
            is_done = totalsize > 0 and read >= totalsize
            if now - last_print[0] < 0.5 and not is_done:
                return
            last_print[0] = now

            elapsed = max(now - start_time, 0.001)
            speed = read / elapsed  # bytes/sec, average so far
            speed_kb = speed / 1024

            if totalsize > 0:
                percent = min(100, read * 100 // totalsize)
                remaining = max(totalsize - read, 0)
                eta = remaining / speed if speed > 0 else float('inf')
                eta_str = f"{int(eta // 60)}m{int(eta % 60):02d}s" if eta != float('inf') else "?"
                print(f"\rDownloading... {percent}%  "
                    f"{read/1024/1024:.1f}/{totalsize/1024/1024:.1f} MB  "
                    f"{speed_kb:.1f} KB/s  ETA {eta_str}   ",
                    end="", flush=True)
            else:
                print(f"\rDownloading... {read/1024/1024:.1f} MB  {speed_kb:.1f} KB/s   ",
                    end="", flush=True)

            if is_done:
                print()  # newline once complete

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
                if proxy is not None and check_package('edge_odys'):
                    from edge_odys.xdownload import XDownloader
                    xdown = XDownloader()
                    xdown.download(url, zip_path,
                                   proxy_url=proxy.http, proxys_url=proxy.https,
                                   prog_hook=prog_hook)
                else:
                    if proxy is not None:
                        proxy_handler = request.ProxyHandler({'http': proxy.http, 'https': proxy.https})
                        opener = urllib.request.build_opener(proxy_handler)
                        request.install_opener(opener)

                    # Original single-stream fallback path.
                    request.urlretrieve(url, zip_path,
                           reporthook=progress_hook if prog_hook is None else prog_hook)

            except (IOError, OSError, RuntimeError) as e:
                print(f"Failed to download {url}: {e}")
                print(f'PROXY: {proxy}')

        if extract_check:
            return extract_check_jretree(zip_path, target_dir)
            '''
            target_dir = Path.joinpath(target_dir, filename + '-extract')
            try: shutil.rmtree(target_dir)
            except: pass

            print(f"Extracting {filename} ...")
            if filename.endswith(".zip"):
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(target_dir)
            elif filename.endswith(".gz") or filename.endswith(".tgz"):
                import tarfile
                with tarfile.open(zip_path, 'r:gz') as t:
                    t.extractall(target_dir)

            ext_root = guess_jretree(target_dir)
            if ext_root is None and (filename.endswith(".zip") or filename.endswith(".gz")):
                raise RuntimeError("JRE extraction failed")
            return ext_root
            '''

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
