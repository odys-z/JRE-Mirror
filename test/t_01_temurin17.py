import os.path
import shutil
import unittest

from src.jre_mirror.temurin17 import TemurinMirror

class Temurin17Test(unittest.TestCase):

    def test_jre(self):
        # _bins = 'bins'
        test_json = 't_01_list.test.json'
        list_json = 't_01_list.json'
        shutil.copy(test_json, list_json)

        try: os.remove(f'{list_json}.lock')
        except: pass

        # Anson.java_src('semanticshare')
        # res = cast(Temurin17Release, Anson.from_file(list_json))
        # mirror = TemurinMirror(res)
        # try:
        #     while not mirror.lock(list_json):
        #         time.sleep(0.5)
        #     mirror.resolve_to(_bins, extract_check=True)
        #     mirror.release.save(list_json)
        # finally:
        #     mirror.unlock(list_json)
        res = TemurinMirror.sync(list_json)

        self.assertTrue(len(res.resources) > 0)
        for r in res.resources:
            print(r)
            jre_size = os.stat(os.path.join(TemurinMirror.bins, r)).st_size
            self.assertTrue(1024 * 1024 * 28 < jre_size < 1024 * 1024 * 1024)
            self.assertTrue(os.path.isdir(f'bins/{r}-extract'))
