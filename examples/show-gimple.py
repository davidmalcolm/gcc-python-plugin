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

# Sample python script, to be run by our gcc plugin
# Show the GIMPLE form of each function, using GraphViz
import gcc
from gccutils import get_src_for_loc, cfg_to_dot, invoke_dot

# We'll implement this as a custom pass, to be called directly after the
# builtin "cfg" pass, which generates the CFG:

class ShowGimple(gcc.GimplePass):
    def execute(self, fun):
        # (the CFG should be set up by this point, and the GIMPLE is not yet
        # in SSA form)
        if fun and fun.cfg:
            dot = cfg_to_dot(fun.cfg, fun.decl.name)
            # print dot
            invoke_dot(dot)

ps = ShowGimple(name='show-gimple')
ps.register_after('cfg')
