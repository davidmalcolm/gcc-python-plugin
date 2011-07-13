#   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011 Red Hat, Inc.
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

# Verify behavior of the gcc.Parameter class
import gcc
help(gcc.Parameter)

params = gcc.get_parameters()
assert isinstance(params, dict)

def print_param_named(name):
    print(name)
    param = params[name]
    assert isinstance(param, gcc.Parameter)
    for attr in ('option',
                 'current_value', 'default_value',  'max_value', 'min_value',
                 'help'):
        print('  param.%s: %r' % (attr, getattr(param, attr)))

print_param_named('struct-reorg-cold-struct-ratio')
print_param_named('predictable-branch-outcome')

# Verify that paramters can be set via "current_value":
p = params['predictable-branch-outcome']
assert p.current_value > 0
p.current_value = 0
assert p.current_value == 0
