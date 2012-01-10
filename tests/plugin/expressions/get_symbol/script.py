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

import gcc

from gccutils import Table

t = Table(['Class', 'get_symbol()'],
          sepchar='=')

for name in sorted(dir(gcc)):
    obj = getattr(gcc, name)
    if hasattr(obj, 'get_symbol'):
        try:
            sym = obj.get_symbol()
        except TypeError:
            continue
        if sym != '<<< ??? >>>':
            t.add_row((':py:class:`gcc.%s`' % name,
                       '`%s`' % sym.strip()))

from six import StringIO
s = StringIO()
t.write(s)

for line in s.getvalue().splitlines():
    print('   ' + line.rstrip())
print('\n')
