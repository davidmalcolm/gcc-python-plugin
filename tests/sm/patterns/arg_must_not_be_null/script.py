# -*- coding: utf-8 -*-
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

from sm import main
from sm.parser import parse_string

SCRIPT = '''
sm example_usage_of_nonnull_arg {
  stateful decl any_pointer ptr;

  ptr.all:
    { ptr = 0 } => ptr.null;

  ptr.null:
    $arg_must_not_be_null$
      => {{
            error('%s() was called with NULL %s as argument %i/index %i: %r'
                  % (function, ptr, argnumber, argindex, parameter))
         }};
}
'''

checker = parse_string(SCRIPT)
main([checker])
