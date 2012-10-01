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
sm malloc_checker {
  state decl any_pointer ptr;

  ptr.all:
    { ptr = malloc() } =>  ptr.unknown;

  ptr.all:
    { ptr = 0 } =>  ptr.null;

  ptr.unknown, ptr.null, ptr.nonnull:
      { ptr == 0 } => true=ptr.null, false=ptr.nonnull
    | { ptr != 0 } => true=ptr.nonnull, false=ptr.null
    ;

  ptr.unknown:
    { *ptr } => { error('use of possibly-NULL pointer %s' % ptr)}, ptr.nonnull;

  ptr.null:
    { *ptr } => { error('use of NULL pointer %s' % ptr)};

  ptr.all, ptr.unknown, ptr.null, ptr.nonnull:
    { free(ptr) } => ptr.free;

  ptr.free:
      { free(ptr) } => { error('double-free of %s' % ptr)}
    | { ptr } => {error('use-after-free of %s' % ptr)}
    ;

  ptr.unknown:
      { memset(ptr) } => { error('use of possibly-NULL pointer %s' % ptr)};

  ptr.null:
      { memset(ptr) } => { error('use of NULL pointer %s' % ptr)};

  ptr.freed:
      { memset(ptr) } => { error('use-after-free of %s' % ptr)};

}
'''

checker = parse_string(SCRIPT)
main([checker])
