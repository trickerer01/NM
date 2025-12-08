import sys

if __package__ is None and not getattr(sys, 'frozen', False):
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import nm

if __name__ == '__main__':
    nm.main(sys.argv[1:])
