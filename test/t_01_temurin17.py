import os.path
import shutil
import unittest

from src.jre_mirror.temurin17 import TemurinMirror

class Temurin17Test(unittest.TestCase):

    def test_jre(self):
        '''
        Download list items, e.g. from https://github.com.
        Remove test/bins for restart actual downloading.
        '''
        test_json = 't_01_list.test.json'
        list_json = 't_01_list.json'
        shutil.copy(test_json, list_json)

        try: os.remove(f'{list_json}.lock')
        except: pass

        res = TemurinMirror.sync(list_json)

        self.assertTrue(len(res.resources) > 0)
        for r in res.resources:
            print(r)
            jre_size = os.stat(os.path.join(TemurinMirror.bins, r)).st_size
            self.assertTrue(1024 * 1024 * 28 < jre_size < 1024 * 1024 * 1024)
            self.assertTrue(os.path.isdir(f'bins/{r}-extract'))
