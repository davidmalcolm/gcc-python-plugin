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

# Verify that we can use gcc.get_translation_units()
import gcc

from gccutils import get_global_typedef

def on_pass_execution(p, data):
    if p.name == 'visibility':
        print('len(gcc.get_translation_units()): %i' % len(gcc.get_translation_units()))
        u = gcc.get_translation_units()[0]
        print('type(u): %s' % type(u))
        print('u.language: %r' % u.language)
        print('type(u.block): %s' % type(u.block))
        for v in u.block.vars:
            if v.name == 'test_typedef':
                print('v.name: %r' % v.name)
                print('type(v): %s' % v)

            if v.name == 'test_var':
                print('v.name: %r' % v.name)
                print('type(v): %s' % v)
        #print 'u.block: %s' % u.block
        #u.block.debug()

        td = get_global_typedef('test_typedef')
        print('td: %s' % td)
        print('td.name: %r' % td.name)
        print('type(td.type): %s' % type(td.type))



gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
