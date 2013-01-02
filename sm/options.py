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

ENABLE_TIMING=0

class Options:
    """
    dump_json: if set to True, then error reports will be written out as
               JSON files with names of the form
                   "INPUTFILENAME.hash.sm.json"
               rather than to stderr, and the presence of such errors will
               not lead to gcc treating the compilation as a failure

    enable_timing: if set to True, dump timing information to stderr
    """
    def __init__(self,
                 cache_errors=True,
                 during_lto=False,
                 dump_json=False,
                 enable_timing=ENABLE_TIMING):
        self.cache_errors = cache_errors
        self.during_lto = during_lto
        self.dump_json = dump_json
        self.enable_timing = enable_timing

