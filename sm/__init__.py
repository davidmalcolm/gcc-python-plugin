#   Copyright 2012, 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012, 2013 Red Hat, Inc.
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

from sm.options import Options
from sm.solver import Context, solve, SHOW_SUPERGRAPH
from sm.utils import Timer

class IpaSmPass(gcc.IpaPass):
    def __init__(self, checkers, options, selftest):
        gcc.IpaPass.__init__(self, 'sm-ipa-pass')
        self.checkers = checkers
        self.options = options
        self.selftest = selftest

    def execute(self):
        if self.options.during_lto:
            # LTO pass:
            # Only run the analysis during the link, within lto1, not for each
            # cc1 invocation:
            if not gcc.is_lto():
                return

        if 0:
            from gccutils import callgraph_to_dot, invoke_dot
            dot = callgraph_to_dot()
            invoke_dot(dot, name='callgraph')

        # Interprocedural implementation, using the supergraph of all calls:
        from gccutils.graph.supergraph import Supergraph
        sg = Supergraph(split_phi_nodes=True, add_fake_entry_node=True)
        if SHOW_SUPERGRAPH:
            dot = sg.to_dot('supergraph')
            from gccutils import invoke_dot
            # print(dot)
            invoke_dot(dot, name='supergraph')

        for checker in self.checkers:
            for sm in checker.sms:
                ctxt = Context(checker, sm, sg, self.options)

                def run():
                    with Timer(ctxt, 'running %s' % sm.name):
                        solve(ctxt, 'solution', self.selftest)

                if self.options.enable_profile:
                    # Profiled version:
                    import cProfile
                    prof_filename = '%s.%s.sm-profile' % (gcc.get_dump_base_name(),
                                                          sm.name)
                    try:
                        cProfile.runctx('run()',
                                        globals(), locals(),
                                        filename=prof_filename)
                    finally:
                        import pstats
                        prof = pstats.Stats(prof_filename)
                        prof.sort_stats('cumulative').print_stats(20)
                else:
                    # Unprofiled version:
                    run()

def main(checkers, options=None, selftest=None):
    if not options:
        options = Options()

    # Run as an interprocedural pass (over SSA gimple), potentially
    # during lto1:
    ps = IpaSmPass(checkers, options, selftest)
    ps.register_before('whole-program')

