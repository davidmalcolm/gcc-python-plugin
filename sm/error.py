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

class Error:
    # A stored error
    def __init__(self, expnode, match, msg):
        self.expnode = expnode
        self.match = match
        self.msg = msg

    @property
    def gccloc(self):
        gccloc = self.expnode.innernode.get_gcc_loc()
        if gccloc is None:
            gccloc = self.function.end
        return gccloc

    @property
    def function(self):
        return self.expnode.function

    def __lt__(self, other):
        # Provide a sort order, so that they sort into source order
        return self.gccloc < other.gccloc

    def emit(self, ctxt, expgraph):
        """
        Display the error
        """
        from gccutils import error, inform
        loc = self.gccloc
        error(loc, self.msg)
        path = expgraph.get_shortest_path_to(self.expnode)
        # ctxt.debug('path: %r' % path)
        for expedge in path:
            # ctxt.debug(expnode)
            # FIXME: this needs to respect the StateVar, in case of a returned value...
            # we need to track changes to the value of the specific StateVar (but we can't, because it's a copy each time.... grrr...)
            # we should also report relevant aliasing information
            # ("foo" passed to fn bar as "baz"; "baz" returned from fn bar into "foo")
            # TODO: backtrace down the path, tracking the StateVar aliases of interest...

            stateful_gccvar = self.match.get_stateful_gccvar(ctxt)
            srcstate = expedge.srcnode.shape.get_state(stateful_gccvar)
            dststate = expedge.dstnode.shape.get_state(stateful_gccvar)
            # (they will always be equal for ssanames, so we have to work on
            # the underlying vars)
            if srcstate != dststate:
                gccloc = expedge.srcnode.innernode.get_gcc_loc()
                if gccloc:
                    if 1:
                        # Describe state change:
                        if expedge.match:
                            desc = expedge.match.description(ctxt)
                        else:
                            continue
                    else:
                        # Debugging information on state change:
                        desc = ('%s: %s -> %s'
                               % (ctxt.sm.name, srcstate, dststate))
                    inform(gccloc, desc)

        # repeat the message at the end of the path:
        if len(path) > 1:
            gccloc = path[-1].dstnode.innernode.get_gcc_loc()
            if gccloc:
                inform(gccloc, self.msg)

