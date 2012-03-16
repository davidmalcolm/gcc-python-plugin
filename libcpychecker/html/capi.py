"""
Module to help figure out urls for Python C-API functions.
"""
from os.path import dirname, abspath, join
HERE = dirname(abspath(__file__))

# Map functions to their modules.
FUNCTIONS = {}

def init():
    """Initialize this module"""
    for line in open(join(HERE, 'c-api.txt')):
        line = line.strip()
        if line.startswith('#'):
            continue
        module, function = line.split()
        FUNCTIONS[function] = module
    del module, function

def get_url(function):
    """Get a url for a function"""
    module = FUNCTIONS.get(function)
    if module:
        return "http://docs.python.org/c-api/%s.html#%s" % (module, function)
    else:
        return None

init() # This is done once, upon import
