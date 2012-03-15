#   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011, 2012 Red Hat, Inc.
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
HTML visualizations, with de-duplication.

GCC diagnostic messages are buffered up within Report instances and eventually
flushed, allowing us to de-duplicate error reports.
"""

import gcc
from gccutils import get_src_for_loc, check_isinstance
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

def describe_trace(trace, report, annotator):
    """
    Buffer up more details about the path through the function that
    leads to the error, using report.add_inform()
    """
    awaiting_target = None
    for t in trace.transitions:
        log('transition: %s', t)
        srcloc = t.src.get_gcc_loc_or_none()
        if t.desc:
            if srcloc:
                report.add_inform(t.src.get_gcc_loc(report.fun),
                                  ('%s at: %s'
                                   % (t.desc, get_src_for_loc(srcloc))))
            else:
                report.add_inform(t.src.get_gcc_loc(report.fun),
                                  '%s' % t.desc)

            if t.src.loc.bb != t.dest.loc.bb:
                # Tell the user where conditionals reach:
                destloc = t.dest.get_gcc_loc_or_none()
                if destloc:
                    report.add_inform(destloc,
                                      'reaching: %s' % get_src_for_loc(destloc))

        if annotator:
            notes = annotator.get_notes(t)
            for note in notes:
                if note.loc and note.loc == srcloc:
                    report.add_inform(note.loc, note.msg)

class Reporter:
    """
    Error-reporting interface.  Gathers information, sending it to GCC's
    regular diagnostic interface, but also storing it for e.g. HTML dumps

    Error reports can be de-duplicated by finding sufficiently similar Report
    instances, and only fully flushing one of them within each equivalence
    class
    """
    def __init__(self):
        self.reports = []
        self._got_warnings = False

    def make_warning(self, fun, loc, msg):
        assert isinstance(fun, gcc.Function)
        assert isinstance(loc, gcc.Location)

        self._got_warnings = True

        w = Report(fun, loc, msg)
        self.reports.append(w)

        w.add_warning(loc, msg)

        return w

    def make_debug_dump(self, fun, loc, msg):
        assert isinstance(fun, gcc.Function)
        assert isinstance(loc, gcc.Location)
        r = Report(fun, loc, msg)
        self.reports.append(r)
        return r

    def got_warnings(self):
        return self._got_warnings

    def to_json(self, fun):
        result = dict(filename=fun.start.file,
                      function=dict(name=fun.decl.name,
                                    # line number range:
                                    lines=(fun.start.line,
                                           fun.end.line)),
                      reports=[])
        for report in self.reports:
            result['reports'].append(report.to_json(fun))
        return result

    def dump_json(self, fun, filename):
        js = self.to_json(fun)
        from json import dump, dumps
        with open(filename, 'w') as f:
            dump(js, f, sort_keys=True, indent=4)
        print(dumps(js, sort_keys=True, indent=4))

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

    def remove_duplicates(self):
        """
        Try to organize Report instances into equivalence classes, and only
        keep the first Report within each class
        """
        for report in self.reports[:]:
            # The report might have been removed during the iteration:
            if report.is_duplicate:
                continue
            for candidate in self.reports[:]:
                if report != candidate and not report.is_duplicate:
                    if candidate.is_duplicate_of(report):
                        report.add_duplicate(candidate)
                        self.reports.remove(candidate)

        # Add a note to each report that survived about any duplicates:
        for report in self.reports:
            if report.duplicates:
                report.add_note(report.loc,
                                ('found %i similar trace(s) to this'
                                 % len(report.duplicates)))

    def flush(self):
        for r in self.reports:
            r.flush()

class SavedDiagnostic:
    """
    A saved GCC diagnostic, which we can choose to emit or suppress at a later
    date
    """
    def __init__(self, loc, msg):
        assert isinstance(loc, gcc.Location)
        assert isinstance(msg, str)
        self.loc = loc
        self.msg = msg

class SavedWarning(SavedDiagnostic):
    def flush(self):
        gcc.warning(self.loc, self.msg)

class SavedInform(SavedDiagnostic):
    def flush(self):
        gcc.inform(self.loc, self.msg)

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
        self._saved_diagnostics = [] # list of SavedDiagnostic

        # De-duplication handling:
        self.is_duplicate = False
        self.duplicates = [] # list of Report

    def add_warning(self, loc, msg):
        # Add a gcc.warning() to the buffer of GCC diagnostics
        self._saved_diagnostics.append(SavedWarning(loc, msg))

    def add_inform(self, loc, msg):
        # Add a gcc.inform() to the buffer of GCC diagnostics
        self._saved_diagnostics.append(SavedInform(loc, msg))

    def flush(self):
        # Flush the buffer of GCC diagnostics
        for d in self._saved_diagnostics:
            d.flush()

    def add_trace(self, trace, annotator=None):
        self.trace = trace
        self._annotators[trace] = annotator
        describe_trace(trace, self, annotator)

    def add_note(self, loc, msg):
        """
        Add a note at the given location.  This is added both to
        the buffer of GCC diagnostics, and also to a saved list that's
        available to the HTML renderer.
        """
        self.add_inform(loc, msg)
        note = Note(loc, msg)
        self.notes.append(note)
        return note

    def get_annotator_for_trace(self, trace):
        return self._annotators.get(trace)

    def is_duplicate_of(self, other):
        check_isinstance(other, Report)

        # Simplistic equivalence classes for now:
        # the same function, source location, and message; everything
        # else can be different
        if self.fun != other.fun:
            return False
        if self.loc != other.loc:
            return False
        if self.msg != other.msg:
            return False

        return True

    def add_duplicate(self, other):
        assert not self.is_duplicate
        self.duplicates.append(other)
        other.is_duplicate = True

    def to_json(self, fun):
        assert self.trace
        result = dict(message=self.msg,
                      severity='warning', # FIXME
                      states=[])
        # Generate a list of (state, desc) pairs, putting the desc from the
        # transition into source state; the final state will have an empty
        # string
        pairs = []
        for t_iter in self.trace.transitions:
            pairs.append( (t_iter.src, t_iter.desc) )
        pairs.append( (self.trace.transitions[-1].dest, None) )
        for i, (s_iter, desc) in enumerate(pairs):
            result['states'].append(s_iter.as_json(desc))
        result['notes'] = [dict(location=location_as_json(note.loc),
                                message=note.msg)
                           for note in self.notes]
        return result


class Note:
    """
    A note within a self
    """
    def __init__(self, loc, msg):
        self.loc = loc
        self.msg = msg


def location_as_json(loc):
    if loc:
        return (dict(line=loc.line,
                     column=loc.column),
                dict(line=loc.line,
                     column=loc.column))
    else:
        return None
