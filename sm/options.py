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

ENABLE_LOG=0
ENABLE_DEBUG=0
ENABLE_PROFILE=0
ENABLE_TIMING=0
SHOW_SUPERGRAPH=0
SHOW_EXPLODED_GRAPH=0
DUMP_SOLUTION=0
SHOW_SOLUTION=0

class Options:
    """
    dump_json: if set to True, then error reports will be written out as
               JSON files with names of the form
                   "INPUTFILENAME.hash.sm.json"
               rather than to stderr, and the presence of such errors will
               not lead to gcc treating the compilation as a failure

    enable_log:

       If set to True, emit medium-level debug information to stderr

    enable_debug:

       If set to True, emit low-level debug information to stderr

    enable_profile:

       If set to True, use CPython's cProfile module to generate a profile
       of the activity for each checker.  The top 20 longest functions calls
       (cumulatively) will be emitted to stdout, and a profile will be
       written to a file for each checker that was run, suitable for viewing
       e.g. by RunSnakeRun

       Given an input file "foo.c" and checkers "bar" and "baz", it will
       write out files:
          foo.c.bar.sm-profile
          foo.c.baz.sm-profile

    enable_timing: if set to True, dump timing information to stderr

    show_supergraph:

        If set to True, render and display a png visualization of the
        supergraph

    show_exploded_graph:

        If set to True, render and display a png visualization of the
        supergraph exploded by state, before and after pruning valid paths

    dump_solution:

        If set to True, print detailed information about the solver's
        internal state to stderr

    show_solution:

        If set to True, render and display a png visualization of the
        solver's internal state
    """
    def __init__(self,
                 cache_errors=True,
                 during_lto=False,
                 dump_json=False,
                 enable_log = ENABLE_LOG,
                 enable_debug = ENABLE_DEBUG,
                 enable_profile=ENABLE_PROFILE,
                 enable_timing=ENABLE_TIMING,
                 show_supergraph=SHOW_SUPERGRAPH,
                 show_exploded_graph=SHOW_EXPLODED_GRAPH,
                 dump_solution=DUMP_SOLUTION,
                 show_solution=SHOW_SOLUTION):
        self.cache_errors = cache_errors
        self.during_lto = during_lto
        self.dump_json = dump_json
        self.enable_log = enable_log
        self.enable_debug = enable_debug
        self.enable_profile = enable_profile
        self.enable_timing = enable_timing
        self.show_supergraph = show_supergraph
        self.show_exploded_graph = show_exploded_graph
        self.dump_solution = dump_solution
        self.show_solution = show_solution

