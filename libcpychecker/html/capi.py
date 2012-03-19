#   Copyright 2012 Buck Golemon <buck@yelp.com>
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.
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
