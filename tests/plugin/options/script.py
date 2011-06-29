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

# Verify behavior of the gcc.Option class
import gcc
help(gcc.Option)

from pprint import pprint

def print_option(option):
    print(option)
    for attr in ('text',
                 'help',
                 'is_warning',
                 'is_optimization',
                 'is_driver',
                 'is_target'):
        print('    option.%s: %r' % (attr, getattr(option, attr)))

# Test direct construction:
option = gcc.Option('-funroll-loops')
print_option(option)

# Test gcc.get_option_list():
options = gcc.get_option_list()
assert isinstance(options, list)
for i, option in enumerate(options):
    assert isinstance(option, gcc.Option)
    # (Turn this on to dump all options in order of gcc's enum opt_code)
    if 0:
        print('option[%i]:' % i)
        print_option(option)

# Test gcc.get_option_dict():
options = gcc.get_option_dict()
assert isinstance(options, dict)
for optname in ('-fjump-tables', '-Os', '-Wuninitialized'):
    option = options[optname]
    print_option(option)

# Verify the option-not-found case:
option = gcc.Option('-foptimize-for-web-scale')
