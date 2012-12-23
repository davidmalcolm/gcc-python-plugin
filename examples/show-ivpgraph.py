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
# Show the "IVP graph": the CFG of all functions, linked by
# interprocedural edges, with a copy of each function repeated
# for each N possible callsites at the top of the stack, so that
# only interprocedurally-valid paths are possible (as well as those
# erroneously present due to the truncation of the stack)

import gcc
from gccutils.graph.supergraph import Supergraph
from gccutils.graph.ivpgraph import IvpGraph
from gccutils import invoke_dot

# We'll implement this as a custom pass, to be called directly after the
# builtin "cfg" pass, which generates the CFG:

class ShowIvpgraph(gcc.SimpleIpaPass):
    def execute(self):
        # (the callgraph should be set up by this point)
        sg = Supergraph(split_phi_nodes=False,
                        add_fake_entry_node=True)
        ivpgraph = IvpGraph(sg, maxlength=2)
        dot = ivpgraph.to_dot('ivpgraph')
        invoke_dot(dot, 'ivpgraph')

ps = ShowIvpgraph(name='show-ivpgraph')
ps.register_before('early_local_cleanups')
