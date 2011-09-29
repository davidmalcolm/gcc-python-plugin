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
from libcpychecker.utils import log

class Annotator:
    """
    A collection of hooks for use when describing a trace (either as text,
    or as an HTML report)

    This allows us to add the annotations to the correct place in the textual
    stream when reporting on flow through a function
    """
    def get_notes(self, transition):
        """
        Return a list of Note instances giving extra information about the
        transition
        """
        raise NotImplementedError

class TestAnnotator(Annotator):
    """
    A sample annotator that adds information to the trace on movement between
    gimple statements
    """
    def get_notes(self, transition):
        result = []
        srcloc = transition.src.get_gcc_loc_or_none()
        if srcloc:
            if transition.src.loc != transition.dest.loc:
                result.append(Note(srcloc,
                                   ('transition from "%s" to "%s"'
                                    % (transition.src.loc.get_stmt(),
                                       transition.dest.loc.get_stmt()))))
        return result

def describe_trace(trace, fun, annotator):
    """
    Print more details about the path through the function that
    leads to the error, using gcc.inform()
    """
    awaiting_target = None
    for t in trace.transitions:
        log('transition: %s', t)
        srcloc = t.src.get_gcc_loc_or_none()
        if t.desc:
            if srcloc:
                gcc.inform(t.src.get_gcc_loc(fun),
                           ('%s at: %s'
                            % (t.desc, get_src_for_loc(srcloc))))
            else:
                gcc.inform(t.src.get_gcc_loc(fun),
                           '%s' % t.desc)

            if t.src.loc.bb != t.dest.loc.bb:
                # Tell the user where conditionals reach:
                destloc = t.dest.get_gcc_loc_or_none()
                if destloc:
                    gcc.inform(destloc,
                               'reaching: %s' % get_src_for_loc(destloc))

        if annotator:
            notes = annotator.get_notes(t)
            for note in notes:
                if note.loc and note.loc == srcloc:
                    gcc.inform(note.loc, note.msg)

class Reporter:
    """
    Error-reporting interface.  Gathers information, sending it to GCC's
    regular diagnostic interface, but also storing it for e.g. HTML dumps
    """
    def __init__(self):
        self.reports = []
        self._got_errors = False

    def make_error(self, fun, loc, msg):
        assert isinstance(fun, gcc.Function)
        assert isinstance(loc, gcc.Location)
        gcc.error(loc, msg)

        self._got_errors = True

        err = Report(fun, loc, msg)
        self.reports.append(err)
        return err

    def make_debug_dump(self, fun, loc, msg):
        assert isinstance(fun, gcc.Function)
        assert isinstance(loc, gcc.Location)
        r = Report(fun, loc, msg)
        self.reports.append(r)
        return r

    def got_errors(self):
        return self._got_errors

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
        self._annotators = {}
        self.notes = []

    def add_trace(self, trace, annotator=None):
        self.trace = trace
        self._annotators[trace] = annotator
        describe_trace(trace, self.fun, annotator)

    def add_note(self, loc, msg):
        gcc.inform(loc, msg)
        note = Note(loc, msg)
        self.notes.append(note)
        return note

    def get_annotator_for_trace(self, trace):
        return self._annotators.get(trace)



class Note:
    """
    A note within a report
    """
    def __init__(self, loc, msg):
        self.loc = loc
        self.msg = msg
