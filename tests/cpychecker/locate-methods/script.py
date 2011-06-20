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

# Verify that libcpychecker can categorize C functions as Python methods
# (and thus know which refcounting rules to apply)
import gcc
from libcpychecker import get_all_PyMethodDef_methods

def on_pass_execution(p, data):
    if p.name == 'visibility':
        methods = get_all_PyMethodDef_methods()
        print('len(methods): %s' % len(methods))
        for i, m in enumerate(methods):
            print('m[%i]:' % i)
            print('  decl: %s' % m[0])
            print('  loc: %s' % m[1])

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
