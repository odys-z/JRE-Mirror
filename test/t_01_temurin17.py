import os.path
import shutil
import time
import unittest
from typing import cast

from anson.io.odysz.anson import Anson

from semanticshare.io.oz.invoke import Temurin17Release
from src.jre_mirror.temurin17 import TemurinMirror

class Temurin17Test(unittest.TestCase):

    def test_jre(self):
        _bins = 'bins'
        jre17_x64_linux = 'OpenJDK17U-jre_x64_linux_hotspot_17.0.17_10.tar.gz'
        test_json = 't_01_list.test.json'
        list_json = 't_01_list.json'
        shutil.copy(test_json, list_json)

        # if os.path.exists(_bins):
        #     shutil.rmtree(_bins)

        Anson.java_src('semanticshare')

        res = cast(Temurin17Release, Anson.from_file(list_json))
        # OpenJDK17U-jre_x64_linux_hotspot_17.0.17_10.tar.gz
        # res.mirroring = [jre17_x64_linux]
        # res.toFile(list_json)

        mirror = TemurinMirror(res)
        while not mirror.lock(list_json):
            time.sleep(0.5)
        mirror.resolve_to(_bins, extract_check=True)
        mirror.release.save(list_json)
        mirror.unlock(list_json)

        jre_size = os.stat(os.path.join(_bins, jre17_x64_linux)).st_size
        self.assertTrue(1024 * 1024 * 28 < jre_size < 1024 * 1024 * 1024)
