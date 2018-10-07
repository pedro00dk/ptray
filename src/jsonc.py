"""
This modules provides a function for reading jsonc files.
"""
import json
import re


"""
Matches comments in jsonc files.
"""
_COMMENT_MATCHER = re.compile(r'\s*//')


def loads(s, encoding=None, cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
    """
    Loads a jsonc file from a string.
    """
    return json.loads(
        ''.join(line for line in s.splitlines() if _COMMENT_MATCHER.search(line) == None),
        cls=cls,
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
        ** kw
    )


def test():
    with open('./specs/disk.jsonc') as specification_file:
        print(loads(specification_file.read()))

if __name__ == '__main__':
    test()