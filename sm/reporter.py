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

from collections import namedtuple
import os

import gccutils

class Note(namedtuple('Note', ('gccloc', 'msg'))):
    def as_json(self):
        return dict(loc=gccloc_as_json(self.gccloc),
                    message=self.msg)

def gccloc_as_json(gccloc):
    return dict(givenfilename=gccloc.file,
                actualfilename=os.path.abspath(gccloc.file),
                line=gccloc.line,
                column=gccloc.column)

class Report:
    def __init__(self, sm, err, notes):
        self.sm = sm
        self.err = err
        self.notes = notes

    def as_json(self):
        sm_as_json = dict(name=self.sm.name)
        jsonic = dict(sm=sm_as_json,
                      loc=gccloc_as_json(self.err.gccloc),
                      message=self.err.msg,
                      notes=[])
        for note in self.notes:
            jsonic['notes'].append(note.as_json())

        return jsonic

class Reporter:
    def add(self, report):
        raise NotImplementedError

class StderrReporter(Reporter):
    def __init__(self):
        self.curfun = None
        self.curfile = None

    def add(self, report):
        err = report.err
        gccloc = err.gccloc
        if err.function != self.curfun or gccloc.file != self.curfile:
            # Fake the function-based output
            # e.g.:
            #    "tests/sm/examples/malloc-checker/input.c: In function 'use_after_free':"
            import sys
            sys.stderr.write("%s: In function '%s':\n"
                             % (gccloc.file, err.function.decl.name))
            self.curfun = err.function
            self.curfile = gccloc.file
            import sys
        gccutils.error(report.err.gccloc, report.err.msg)
        self.curfun = err.function
        self.curfun = err.function

        for note in report.notes:
            gccutils.inform(note.gccloc, note.msg)

class JsonReporter(Reporter):
    def add(self, report):
        import json as jsonmod
        import hashlib

        jsonobj = report.as_json()
        jsonsrc = jsonmod.dumps(jsonobj,
                                sort_keys=True,
                                indent=4, separators=(',', ': '))

        # Use the sha-1 hash of the report to create a unique filename:
        hexdigest = hashlib.sha1(jsonsrc).hexdigest()
        filename = report.err.gccloc.file + '.%s.sm.json' % hexdigest
        with open(filename, 'w') as f:
            f.write(jsonsrc)
