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

"""
Error reporting interface, supporting regular GCC messages plus higher-level
HTML visualizations
"""

import gcc
from gccutils import get_src_for_loc
from libcpychecker.visualizations import HtmlRenderer
from PyArg_ParseTuple import log

def describe_trace(trace, fun):
    """
    Print more details about the path through the function that
    leads to the error, using gcc.inform()
    """
    awaiting_target = None
    for t in trace.transitions:
        log('transition: %s' % t)
        if t.desc:
            srcloc = t.src.get_gcc_loc_or_none()
            if srcloc:
                gcc.inform(t.src.get_gcc_loc(fun),
                           ('when %s at: %s'
                            % (t.desc, get_src_for_loc(srcloc))))
            else:
                gcc.inform(t.src.get_gcc_loc(fun),
                           'when %s' % t.desc)

            if t.src.loc.bb != t.dest.loc.bb:
                # Tell the user where conditionals reach:
                destloc = t.dest.get_gcc_loc_or_none()
                if destloc:
                    gcc.inform(destloc,
                               'reaching: %s' % get_src_for_loc(destloc))

class Reporter:
    """
    Error-reporting interface.  Gathers information, sending it to GCC's
    regular diagnostic interface, but also storing it for e.g. HTML dumps
    """
    def __init__(self):
        self.reports = []

    def make_error(self, fun, loc, msg):
        assert isinstance(fun, gcc.Function)
        assert isinstance(loc, gcc.Location)
        gcc.error(loc, msg)

        err = Report(fun, loc, msg)
        self.reports.append(err)
        return err

    def got_errors(self):
        return self.reports != []

    def to_html(self, fun):
        # (FIXME: eliminate self.fun from HtmlRenderer and the above arg)
        r = HtmlRenderer(fun)
        html = r.make_header()
        for report in self.reports:
            html += r.make_report(report)
        html += r.make_footer()
        return html

    def dump_html(self, fun, filename):
        html = self.to_html(fun)
        with open(filename, 'w') as f:
            f.write(html)


class Report:
    """
    Data about a particular bug found by the checker
    """
    def __init__(self, fun, loc, msg):
        self.fun = fun
        self.loc = loc
        self.msg = msg
        self.trace = None
        self.notes = []

    def add_trace(self, trace):
        self.trace = trace
        describe_trace(trace, self.fun)

    def add_note(self, loc, msg):
        gcc.inform(loc, msg)
        note = Note(loc, msg)
        self.notes.append(note)
        return note


class Note:
    """
    A note within a report
    """
    def __init__(self, loc, msg):
        self.loc = loc
        self.msg = msg
