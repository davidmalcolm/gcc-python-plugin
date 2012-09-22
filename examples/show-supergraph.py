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

# Sample python script, to be run by our gcc plugin
# Show the "supergraph": the CFG of all functions, linked by
# interproceduraledges:
import gcc
from gccutils.graph import Supergraph
from gccutils import invoke_dot

# We'll implement this as a custom pass, to be called directly after the
# builtin "cfg" pass, which generates the CFG:

class ShowSupergraph(gcc.SimpleIpaPass):
    def execute(self):
        # (the callgraph should be set up by this point)
        sg = Supergraph()
        dot = sg.to_dot('supergraph')
        invoke_dot(dot)

ps = ShowSupergraph(name='show-supergraph')
ps.register_before('early_local_cleanups')
