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

from sm.solver import Context, solve

class NonIpaSmPass(gcc.GimplePass):
    def __init__(self, checkers):
        gcc.GimplePass.__init__(self, 'sm-pass-gimple')
        self.checkers = checkers

    def execute(self, fun):
        if 0:
            print(fun)
            print(self.checkers)

        if 0:
            # Dump location information
            for loc in get_locations(fun):
                print(loc)
                for prevloc in loc.prev_locs():
                    print('  prev: %s' % prevloc)
                for nextloc in loc.next_locs():
                    print('  next: %s' % nextloc)

        #print('locals: %s' % fun.local_decls)
        #print('args: %s' % fun.decl.arguments)
        for checker in self.checkers:
            for sm in checker.sms:
                vars_ = fun.local_decls + fun.decl.arguments
                if 0:
                    print('vars_: %s' % vars_)

                for var in vars_:
                    if 0:
                        print(var)
                        print(var.type)
                    if isinstance(var.type, gcc.PointerType):
                        # got pointer type
                        ctxt = Context(sm, var)
                        #print('ctxt: %r' % ctxt)

                        # Non-interprocedural implementation, using just the StmtGraph of the fun:
                        from gccutils.graph import StmtGraph
                        graph = StmtGraph(fun)
                        solve(fun, ctxt, graph)

class IpaSmPass(gcc.SimpleIpaPass):
    def __init__(self, checkers):
        gcc.SimpleIpaPass.__init__(self, 'sm-pass-gimple')
        self.checkers = checkers

    def execute(self):
        if 0:
            from gccutils import callgraph_to_dot, invoke_dot
            dot = callgraph_to_dot()
            invoke_dot(dot)

        # Interprocedural implementation, using the supergraph of all calls:
        from gccutils.graph import Supergraph
        sg = Supergraph()
        if 0:
            dot = sg.to_dot('supergraph')
            from gccutils import invoke_dot
            print(dot)
            invoke_dot(dot)

        for node in gcc.get_callgraph_nodes():
            fun = node.decl.function
            if fun:
                self.analyze_function(fun, sg)

    def analyze_function(self, fun, sg):
        #print('locals: %s' % fun.local_decls)
        #print('args: %s' % fun.decl.arguments)
        for checker in self.checkers:
            for sm in checker.sms:
                vars_ = fun.local_decls + fun.decl.arguments
                if 0:
                    print('vars_: %s' % vars_)


                for var in vars_:
                    if 0:
                        print(var)
                        print(var.type)
                    if isinstance(var.type, gcc.PointerType):
                        # got pointer type
                        ctxt = Context(sm, var)
                        #print('ctxt: %r' % ctxt)
                        solve(fun, ctxt, sg)

def main(checkers):
    if 1:
        ps = NonIpaSmPass(checkers)
        ps.register_before('*warn_function_return')
    else:
        ps = IpaSmPass(checkers)
        ps.register_before('early_local_cleanups') # looks like we can only register within the top-level

# TODO: doing it via an IPA pass make us lose the "In function 'use_after_free':" headers
