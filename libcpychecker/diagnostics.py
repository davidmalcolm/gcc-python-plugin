#   Copyright 2011, 2012, 2013 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011, 2012, 2013 Red Hat, Inc.
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

import sys

from firehose.report import Issue, Location, File, Function, \
    Point, Message, Notes, Trace, State

import gcc
from gccutils import get_src_for_loc, check_isinstance
from libcpychecker.visualizations import HtmlRenderer
from libcpychecker.utils import log


# Firehose support
class CpycheckerIssue(Issue):
    """
    Subclass of firehose.report.Issue, which adds the concept
    of adding notes at the end of the trace in the gcc output,
    mostly for byte-for-byte compatibility with old stderr in the
    selftests
    """
    def __init__(self,
                 cwe,
                 testid,
                 location,
                 message,
                 notes,
                 trace):
        # We don't want any of our testids to be None:
        assert isinstance(testid, str)

        Issue.__init__(self, cwe, testid, location, message, notes, trace)

        self.initial_notes = []
        self.final_notes = []

class WrappedGccLocation(Location):
    """
    A firehose.report.Location
    wrapping a gcc.Location
    """
    def __init__(self, gccloc, funcname):
        self.gccloc = gccloc

        if funcname:
            function = Function(funcname)
        else:
            function = None
        if gccloc:
            file_ = File(givenpath=gccloc.file,
                         abspath=None)
            point = Point(line=gccloc.line,
                          column=gccloc.column)
        else:
            file_ = File(givenpath='FIXME',
                         abspath=None)
            point = None
        Location.__init__(self,
                          file=file_,
                          function=function,
                          point=point)

class WrappedAbsinterpLocation(WrappedGccLocation):
    """
    A firehose.report.Location that wraps a libcpychecker.absinterp.Location
    """
    def __init__(self, loc, funcname):
        self.loc = loc
        gccloc = loc.get_gcc_loc()
        WrappedGccLocation.__init__(self, gccloc, funcname)

class CustomState(State):
    '''
    A firehose.report.State, but with hooks for byte-for-byte compat with
    old output
    '''
    def __init__(self, *args, **kwargs):
        State.__init__(self, *args, **kwargs)
        self.extra_notes = []

    def add_note(self, text):
        assert isinstance(text, str)
        if self.notes is None:
            self.notes = Notes(text)
        else:
            self.extra_notes.append(text)

def make_issue(funcname, gccloc, msg, testid, cwe):
    r = CpycheckerIssue(cwe=cwe,
                        testid=testid,
                        location=WrappedGccLocation(gccloc, funcname),
                        message=Message(text=msg),
                        notes=None,
                        trace=None)
    return r



class Annotator:
    """
    A collection of hooks for use when describing a trace (either as text,
    or as an HTML report)

    This allows us to add the annotations to the correct place in the textual
    stream when reporting on flow through a function
    """
    def get_notes(self, transition):
        """
        Return a list of str instances giving extra information about the
        transition
        """
        raise NotImplementedError

def make_firehose_trace(funcname, trace, annotator):
    """
    input is a libcpychecker.absinterp.Trace
    output is a firehose.report.Trace (aka a Trace within this module)
    """
    result = Trace([])
    for t in trace.transitions:
        log('transition: %s', t)
        def add_state(s_in, is_src):
            srcloc = s_in.get_gcc_loc_or_none()
            if srcloc:
                location=WrappedAbsinterpLocation(s_in.loc,
                                                  funcname=funcname)
                s = CustomState(location,
                                notes=None)
                paras = []
                if t.desc and is_src:
                    s.add_note(t.desc)

                if annotator:
                    notes = annotator.get_notes(t)
                    for note in notes:
                        s.add_note(note)

                result.add_state(s)
        add_state(t.src, True)
    add_state(t.dest, False)

    return result

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
                result.append('transition from "%s" to "%s"'
                              % (transition.src.loc.get_stmt(),
                                 transition.dest.loc.get_stmt()))
        return result

def is_duplicate_of(r1, r2):
    check_isinstance(r1, Issue)
    check_isinstance(r2, Issue)

    # Simplistic equivalence classes for now:
    # the same function, source location, and message; everything
    # else can be different
    if r1.location.function != r2.location.function:
        return False
    if r1.location.point != r2.location.point:
        return False
    if r1.message != r2.message:
        return False

    return True

class Reporter:
    """
    Error-reporting interface.  Gathers information, sending it to GCC's
    regular diagnostic interface, but also storing it for e.g. HTML dumps

    Error reports can be de-duplicated by finding sufficiently similar Report
    instances, and only fully flushing one of them within each equivalence
    class
    """
    def __init__(self, ctxt):
        self.ctxt = ctxt
        self.reports = []
        self._got_warnings = False

    def make_warning(self, fun, loc, msg, testid, cwe):
        assert isinstance(fun, gcc.Function)
        assert isinstance(loc, gcc.Location)

        self._got_warnings = True

        w = make_issue(fun.decl.name, loc, msg, testid, cwe)
        self.reports.append(w)

        return w

    def make_debug_dump(self, fun, loc, msg):
        assert isinstance(fun, gcc.Function)
        assert isinstance(loc, gcc.Location)
        r = Report(fun, loc, msg)
        self.reports.append(r)
        return r

    def got_warnings(self):
        return self._got_warnings

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

        # Set of all Report instances that are a duplicate of another:
        duplicates = set()

        # dict from "primary" Report to the set of its duplicates:
        duplicates_of = {}

        for report in self.reports[:]:
            # The report might have been removed during the iteration:
            if report in duplicates:
                continue
            for candidate in self.reports[:]:
                if report != candidate and report not in duplicates:
                    if is_duplicate_of(candidate, report):
                        duplicates.add(candidate)
                        self.reports.remove(candidate)
                        if report not in duplicates_of:
                            duplicates_of[report] = set([candidate])
                        else:
                            duplicates_of[report].add(candidate)

        # Add a note to each report that survived about any duplicates:
        for report in duplicates_of:
            num_duplicates = len(duplicates_of[report])
            report.final_notes.append((report.location.gccloc,
                                       'found %i similar trace(s) to this'
                                       % num_duplicates))

    def flush(self):
        for r in self.reports:
            emit_report(self.ctxt, r)

def emit_warning(ctxt, loc, msg, funcname, testid, cwe, notes,
                 customfields=None):
    #gcc.warning(loc, msg)

    if notes is not None:
        text = notes
        notes = Notes(text)
    r = make_issue(funcname, loc, msg, testid, cwe)
    r.notes = notes
    r.customfields = customfields

    emit_report(ctxt, r)

def emit_report(ctxt, r):
    emit_report_as_warning(r)
    ctxt.analysis.results.append(r)

def emit_report_as_warning(r):
    # Emit gcc output to stderr, using the Report instance:
    gcc.warning(r.location.gccloc, r.message.text)

    for gccloc, msg in r.initial_notes:
        gcc.inform(gccloc, msg)

    if r.notes:
        sys.stderr.write(r.notes.text)
        if not r.notes.text.endswith('\n'):
            sys.stderr.write('\n')

    if r.trace:
        last_state_with_notes = None
        for state in r.trace.states:
            gccloc = state.location.gccloc
            if last_state_with_notes:
                if last_state_with_notes.location.loc.bb != state.location.loc.bb:
                    # Tell the user where conditionals reach:
                    gcc.inform(gccloc,
                               'reaching: %s' % get_src_for_loc(gccloc))
            last_state_with_notes = None
            #gcc.inform(gccloc,
            #           'reaching: %s' % get_src_for_loc(gccloc))
            if state.notes:
                text = state.notes.text
                if gccloc is not None:
                    text += ' at: %s' % get_src_for_loc(gccloc)
                    last_state_with_notes = state
                gcc.inform(gccloc, text)
                for text in state.extra_notes:
                    gcc.inform(gccloc, text)

    for gccloc, msg in r.final_notes:
        gcc.inform(gccloc, msg)

'''
def describe_trace(trace, report, annotator):
    """
    Buffer up more details about the path through the function that
    leads to the error, using report.add_inform()
    """
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
'''

