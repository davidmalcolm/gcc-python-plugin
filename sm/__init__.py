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

class SmPass(gcc.GimplePass):
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
                        solve(fun, ctxt)

def main(checkers):
    gimple_ps = SmPass(checkers)
    if 1:
        # non-SSA version:
        gimple_ps.register_before('*warn_function_return')
    else:
        # SSA version:
        gimple_ps.register_after('ssa')
