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

import gcc

# Callback without any args:
def my_callback(*args, **kwargs):
    print('my_callback:')
    print('  args: %r' % (args,))
    print('  kwargs: %r' % (kwargs,))

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback)

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback,
                      (1, 2, 3))

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback,
                      foo='bar',
                      baz='qux')

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback,
                      (1, 2, 3),
                      foo='bar',
                      baz='qux')

# (They seem to get invoked in reverse order)

