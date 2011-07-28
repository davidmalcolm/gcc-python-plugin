# -*- coding: utf-8 -*-
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
help(gcc.Rtl)

def on_pass_execution(p, fn):
    if p.properties_provided & gcc.PROP_rtl:
        # For this pass, "fn" will be an instance of gcc.Function:
        if not fn:
            return

        if fn.cfg:
            for bb in fn.cfg.basic_blocks:
                if bb.rtl:
                    for i,stmt in enumerate(bb.rtl):
                        assert isinstance(stmt, gcc.Rtl)
                        # Ensure that we can evaluate the "operands" attribute
                        # on every stmt we see:
                        stmt.operands
                        # print('    rtl[%i]:' % i)

# Wire up our callback:
gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)

