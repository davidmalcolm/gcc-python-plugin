# -*- coding: utf-8 -*-
#   Copyright 2012 Tom Tromey <tromey@redhat.com>
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
from gccutils import pprint

def on_pass_execution(p, fn):
    if p.name == '*warn_function_return':
        assert isinstance(fn, gcc.Function)

        for u in gcc.get_translation_units():
            for v in u.block.vars:
                if v.name == 'arr':
                    print('arr-range-min:%s' % v.type.range.min_value)
                    print('arr-range-max:%s' % v.type.range.max_value)
                if v.name == 'arr2':
                    print('arr2-range:%s' % v.type.range)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)

