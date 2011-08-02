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
# Show the call graph (interprocedural analysis), using GraphViz
import gcc
from gccutils import callgraph_to_dot, invoke_dot

# In theory we could have done this with a custom gcc.Pass registered
# directly after "*build_cgraph_edges".  However, we can only register
# relative to passes of the same kind, and that pass is a
# gcc.GimplePass, which is called per-function, and we want a one-time
# pass instead.
#
# So we instead register a callback on the one-time pass that follows it

def on_pass_execution(p, fn):
    if p.name == '*free_lang_data':
        # The '*free_lang_data' pass is called once, rather than per-function,
        # and occurs immediately after "*build_cgraph_edges", which is the
        # pass that initially builds the callgraph
        #
        # So at this point we're likely to get a good view of the callgraph
        # before further optimization passes manipulate it
        dot = callgraph_to_dot()
        invoke_dot(dot)

gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      on_pass_execution)
