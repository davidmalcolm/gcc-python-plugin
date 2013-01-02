#   Copyright 2012, 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012, 2013 Red Hat, Inc.
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

############################################################################
# Various small utility classes and functions
############################################################################

import time

import gcc

class Timer:
    """
    Context manager for logging the start/finish of a particular activity
    and how long it takes
    """
    def __init__(self, ctxt, name):
        self.ctxt = ctxt
        self.name = name
        self.starttime = time.time()

    def get_elapsed_time(self):
        """Get elapsed time in seconds as a float"""
        curtime = time.time()
        return curtime - self.starttime

    def elapsed_time_as_str(self):
        """Get elapsed time as a string (with units)"""
        elapsed = self.get_elapsed_time()
        result = '%0.3f seconds' % elapsed
        if elapsed > 120:
            result += ' (%i minutes)' % int(elapsed / 60)
        return result

    def __enter__(self):
        self.ctxt.timing('START: %s', self.name)
        self.ctxt._indent += 1

    def __exit__(self, exc_type, exc_value, traceback):
        self.ctxt._indent -= 1
        self.ctxt.timing('%s: %s  TIME TAKEN: %s',
                         'STOP' if exc_type is None else 'ERROR',
                         self.name,
                         self.elapsed_time_as_str())

def simplify(gccexpr):
    if isinstance(gccexpr, gcc.SsaName):
        return gccexpr.var
    return gccexpr

def stateset_to_str(states):
    return '{%s}' % ', '.join([str(state) for state in states])

def equivcls_to_str(equivcls):
    if equivcls is None:
        return 'None'
    return '{%s}' % ', '.join([str(expr) for expr in equivcls])

