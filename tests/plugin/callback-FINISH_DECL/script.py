#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
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

# Test case for gcc.PLUGIN_FINISH_DECL (only present in gcc 4.7 onwards)

import gcc

def finish_decl_cb(*args, **kwargs):
    print('finish_decl_cb(*args=%r, **kwargs=%r)' % (args, kwargs))

gcc.register_callback(gcc.PLUGIN_FINISH_DECL, finish_decl_cb,
                      ('foo', ), bar='baz')
