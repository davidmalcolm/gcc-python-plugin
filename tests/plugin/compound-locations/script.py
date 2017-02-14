#   Copyright 2017 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2017 Red Hat, Inc.
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

import sys

import gcc

# Verify that various aspects of gcc.Location work

def on_pass_execution(p, fn):
    if p.name == '*warn_function_return':
        caret = fn.start.offset_column(13)
        start = fn.start.offset_column(9)
        finish = fn.start.offset_column(17)
        compound = gcc.Location(caret, start, finish)
        gcc.inform(compound, "compound location")
        assert compound.caret == caret
        assert compound.start == start
        assert compound.finish == finish

# Wire up our callback:
gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)

