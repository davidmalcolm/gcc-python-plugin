#   Copyright 2011, 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011, 2013 Red Hat, Inc.
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

# Verify behavior of the gcc.get_*gcc_version() methods
import gcc

def test_version(name, v):
    print(name)
    # print(v)
    # print(tuple(v))
    assert hasattr(v, 'basever')
    assert hasattr(v, 'datestamp')
    assert hasattr(v, 'devphase')
    assert hasattr(v, 'revision')
    assert hasattr(v, 'configuration_arguments')

test_version('gcc.get_gcc_version()',
             gcc.get_gcc_version())

test_version('gcc.get_plugin_gcc_version()',
             gcc.get_plugin_gcc_version())

assert isinstance(gcc.GCC_VERSION, int)
assert gcc.GCC_VERSION >= 4006
