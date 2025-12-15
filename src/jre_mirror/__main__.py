import sys

from .temurin17 import TemurinMirror

if __name__ == "__main__":
    res = TemurinMirror.sync('list.json')
    sys.exit(0)
