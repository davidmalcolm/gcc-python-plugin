#   Copyright 2017 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2017 Red Hat, Inc.
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

# A Python reimplementation of parts of DejaGnu

import re
import unittest

class Directive:
    """
    A "dg-*" directive within an input file.
    """
    def __init__(self, inputfile, linenum, name, args):
        self.inputfile = inputfile
        self.linenum = linenum
        self.name = name
        self.args = self.parse_args(args)
        if len(self.args) == 4:
            m = re.match('\.(-?[0-9]+)', self.args[3])
            offset = int(m.group(1))
            self.linenum += offset

    @staticmethod
    def parse_args(args):
        quoted_group = '"([^"]*)"'
        ws = '\s+'
        m = re.match(quoted_group + ws + quoted_group + ws + '{(.*)}' + ws + '(.+)', args)
        if m:
            return list(m.groups())

        m = re.match(quoted_group + ws + quoted_group + ws + '{(.*)}', args)
        if m:
            return list(m.groups())

        m = re.match(quoted_group + ws + quoted_group, args)
        if m:
            return list(m.groups())

        m = re.match(quoted_group, args)
        if m:
            return list(m.groups())

        m = re.match('(\S+)', args)
        if m:
            return list(m.groups())

        raise ValueError('unparseable directive args: %s' % args)

    def __repr__(self):
        return ('Directive(%r, %r, %r, %r)'
                % (self.inputfile, self.linenum, self.name, self.args))

class ExpectedDiagnostic:
    """
    A dg-warning or dg-error, after parsing
    """
    def __init__(self, kind, pattern, directive):
        self.kind = kind
        self.pattern = pattern
        self.directive = directive
        m = re.match('^([0-9]+): (.*)', self.pattern)
        linenum = directive.linenum
        if m:
            colnum_pattern = m.group(1)
            self.pattern = m.group(2)
        else:
            colnum_pattern = '[0-9]+'
        self.pattern = ('\S+:%i:%s: %s: %s\n'
                        % (linenum, colnum_pattern, self.kind, self.pattern))

    def __repr__(self):
        return ('ExpectedDiagnostic(%r, %r, %r)'
                % (self.kind, self.pattern, self.directive))

class ExpectedMultilineOutput:
    def __init__(self, directive, start, end, lines):
        self.directive = directive
        self.start = start
        self.end = end
        self.lines = lines
        self.pattern = ''.join([re.escape(line) + '\n' for line in self.lines])

    def __repr__(self):
        return ('ExpectedMultilineOutput(%r, %r, %r, %r)'
                % (self.directive, self.start, self.end, self.lines))

class Result:
    """
    A result of a test: a PASS/FAIL, with a message, and an optional
    directive that was being tested.
    """
    def __init__(self, status, directive, message):
        self.status = status
        self.directive = directive
        self.message = message

    def __str__(self):
        result = '%s: ' % self.status
        if self.directive:
            result += ('%s:%i: '
                       % (self.directive.inputfile, self.directive.linenum))
        if self.message:
            result += self.message
        return result

    def __repr__(self):
        return ('Result(%r, %r, %r)'
                % (self.status, self.directive, self.message))

class DgContext:
    """
    A Python reimplementation of DejaGnu
    """
    def __init__(self, inputfiles, verbosity=0):
        self.inputfiles = inputfiles
        self.options = []
        self.verbosity = 0
        self.expected_diagnostics = []
        self.results = []
        self.echo_results = False
        self._cur_multiline_output = None
        self.multiline_ranges = []

    def parse_directives(self, inputfile):
        with open(inputfile, 'r') as f:
            lines = f.read().splitlines()
            for lineidx, line in enumerate(lines):
                directive = self.parse_line(inputfile, lineidx + 1, line)
                if directive:
                    self.handle_directive(directive)

    def parse_line(self, inputfile, linenum, line):
        """
        Look for line content of the form: "{ dg-FOO BAR }"
        """
        m = re.match(r'.*{ (dg-\S+) (.+) }.*', line)
        if m:
            #print(m.groups())
            return Directive(inputfile, linenum, m.group(1), m.group(2))
        elif self._cur_multiline_output:
            self._cur_multiline_output.lines.append(line)

    def handle_directive(self, directive):
        if 0:
            print(directive)
        if directive.name == 'dg-message':
            self.expected_diagnostic('note', directive)
        elif directive.name == 'dg-options':
            self.options.append(directive.args[0])
        elif directive.name == 'dg-do':
            # For now, skip dg-do
            pass
        elif directive.name == 'dg-begin-multiline-output':
            self.begin_multiline_output(directive)
        elif directive.name == 'dg-end-multiline-output':
            self.end_multiline_output(directive)
        else:
            self.on_fail(directive,
                         'unrecognized directive: %s' % directive.name)

    def expected_diagnostic(self, kind, directive):
        message = directive.args[0]
        ed = ExpectedDiagnostic(kind, message, directive)
        self.expected_diagnostics.append(ed)

    def begin_multiline_output(self, directive):
        self._cur_multiline_output = directive
        directive.lines = []

    def end_multiline_output(self, directive):
        start = self._cur_multiline_output.linenum + 1
        end = directive.linenum - 1
        lines = self._cur_multiline_output.lines
        mr = ExpectedMultilineOutput(self._cur_multiline_output,
                                     start, end, lines)
        self.multiline_ranges.append(mr)
        self._cur_multiline_output = None

    def get_args(self):
        return self.options

    def check_result(self, stdout, stderr, exitcode):
        if 0:
            print(self.expected_diagnostics)
        if stdout != '':
            self.on_fail(None, 'non-empty stdout: %r' % stdout)

        # Prune stderr:
        if 0:
            print('Before pruning:\n%s' % stderr)
        stderr = self.prune_stderr(stderr)
        if 0:
            print('After pruning:\n%s' % stderr)
        if stderr != '':
            self.on_fail(None, 'unexpected output on stderr: %r' % stderr)

        # Check exitcode
        if exitcode != 0:
            self.on_fail(None, 'nonzero exit code')

        if 0:
            print(self.results)

    def prune_stderr(self, stderr):
        # Prune lines like this:
        #    tests/plugin/rich-location/input.c: In function 'test_1':
        stderr = re.sub("(\S+: In function '.+':)\n", '', stderr)
        for d in self.expected_diagnostics:
            stderr, count = re.subn(d.pattern, '', stderr, 1)
            if count == 1:
                self.on_pass(d.directive, d.directive.name)
            else:
                self.on_fail(d.directive, 'diagnostic not found')
        for mr in self.multiline_ranges:
            stderr, count = re.subn(mr.pattern, '', stderr, 1)
            if count == 1:
                self.on_pass(mr.directive, 'multiline range')
            else:
                self.on_fail(mr.directive, 'multiline range not found')
        return stderr

    def on_pass(self, directive, issue):
        self.add_result(Result('PASS', directive, issue))

    def on_fail(self, directive, issue):
        self.add_result(Result('FAIL', directive, issue))

    def add_result(self, result):
        if self.echo_results:
            print(str(result))
        self.results.append(result)

    def num_failures(self):
        count = 0
        for r in self.results:
            if r.status == 'FAIL':
                count += 1
        return count

def uses_dg_directives(inputfiles):
    for inputfile in inputfiles:
        with open(inputfile, 'r') as f:
            code = f.read()
            if 'dg-do' in code:
                return True

class Tests(unittest.TestCase):
    def test_parse_line(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        d = ctxt.parse_line(INPUT_FILE, 42,
                            'before /* { dg-something "arg1" "arg2" } */ after')
        self.assertEqual(d.inputfile, INPUT_FILE)
        self.assertEqual(d.linenum, 42)
        self.assertEqual(d.name, 'dg-something')
        self.assertEqual(d.args, ['arg1', 'arg2'])

    def test_nonempty_stdout(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        ctxt.check_result('stray text', '', 0)
        self.assertEqual(len(ctxt.results), 1)
        self.assertEqual(ctxt.results[0].status, 'FAIL')
        self.assertEqual(ctxt.results[0].message,
                         "non-empty stdout: 'stray text'")
        self.assertEqual(ctxt.num_failures(), 1)

    def test_surplus_errors(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        ctxt.check_result('', 'stray text', 0)
        self.assertEqual(len(ctxt.results), 1)
        self.assertEqual(ctxt.results[0].status, 'FAIL')
        self.assertEqual(ctxt.results[0].message,
                         "unexpected output on stderr: 'stray text'")
        self.assertEqual(ctxt.num_failures(), 1)

    def test_dg_message_found(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        d = ctxt.parse_line(INPUT_FILE, 23,
                            'before /* { dg-message "17: hello world" } */ after')
        ctxt.handle_directive(d)
        self.assertEqual(len(ctxt.expected_diagnostics), 1)
        ed = ctxt.expected_diagnostics[0]
        self.assertEqual(ed.kind, 'note')
        self.assertEqual(ed.pattern, '\\S+:23:17: note: hello world\n')

        ctxt.check_result('', INPUT_FILE + ':23:17: note: hello world\n', 0)
        self.assertEqual(len(ctxt.results), 1)
        self.assertEqual(ctxt.results[0].status, 'PASS')
        self.assertEqual(ctxt.results[0].message, 'dg-message')
        self.assertEqual(ctxt.num_failures(), 0)

    def test_dg_message_not_found(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        d = ctxt.parse_line(INPUT_FILE, 23,
                            'before /* { dg-message "17: hello world" } */ after')
        ctxt.handle_directive(d)
        self.assertEqual(len(ctxt.expected_diagnostics), 1)

        # Incorrect line/column:
        ctxt.check_result('', INPUT_FILE + ':24:18: note: hello world\n', 0)
        self.assertEqual(len(ctxt.results), 2)
        self.assertEqual(ctxt.results[0].status, 'FAIL')
        self.assertEqual(ctxt.results[0].message, 'diagnostic not found')
        self.assertEqual(ctxt.results[1].status, 'FAIL')
        self.assertEqual(ctxt.results[1].message,
                         "unexpected output on stderr: 'foo.c:24:18: note: hello world\\n'")
        self.assertEqual(ctxt.num_failures(), 2)

    def test_directive_with_full_args(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        d = ctxt.parse_line(INPUT_FILE, 23,
                            '/* { dg-message "14: hello world" "title" { target *-*-* } .-1 } */')
        self.assertEqual(d.inputfile, INPUT_FILE)
        self.assertEqual(d.linenum, 22)
        self.assertEqual(d.name, 'dg-message')
        self.assertEqual(d.args, ['14: hello world', 'title', ' target *-*-* ', '.-1'])

        ctxt.handle_directive(d)

        self.assertEqual(len(ctxt.expected_diagnostics), 1)
        ed = ctxt.expected_diagnostics[0]
        self.assertEqual(ed.kind, 'note')
        self.assertEqual(ed.pattern, '\\S+:22:14: note: hello world\n')

        self.assertEqual(len(ctxt.expected_diagnostics), 1)

        ctxt.check_result('', INPUT_FILE + ':22:14: note: hello world\n', 0)
        self.assertEqual(ctxt.num_failures(), 0)

    def test_directive_with_full_args_2(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        d = ctxt.parse_line(INPUT_FILE, 23,
                            '/* { dg-message "14: hello world" "" { target *-*-* } .-1 } */')
        self.assertEqual(d.inputfile, INPUT_FILE)
        self.assertEqual(d.linenum, 22)
        self.assertEqual(d.name, 'dg-message')
        self.assertEqual(d.args, ['14: hello world', '', ' target *-*-* ', '.-1'])

        ctxt.handle_directive(d)

        self.assertEqual(len(ctxt.expected_diagnostics), 1)
        ed = ctxt.expected_diagnostics[0]
        self.assertEqual(ed.kind, 'note')
        self.assertEqual(ed.pattern, '\\S+:22:14: note: hello world\n')

        self.assertEqual(len(ctxt.expected_diagnostics), 1)

        ctxt.check_result('', INPUT_FILE + ':22:14: note: hello world\n', 0)
        self.assertEqual(ctxt.num_failures(), 0)

    def test_dg_options(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        d = ctxt.parse_line(INPUT_FILE, 23,
                            '/* { dg-options "-fdiagnostics-show-caret" } */')
        ctxt.handle_directive(d)
        self.assertEqual(ctxt.options, ['-fdiagnostics-show-caret'])

    def test_dg_do(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        d = ctxt.parse_line(INPUT_FILE, 23,
                            '/* { dg-do compile } */')
        ctxt.handle_directive(d)
        self.assertEqual(d.args, ['compile'])

    def test_multiline_ranges(self):
        INPUT_FILE = 'foo.c'
        ctxt = DgContext([INPUT_FILE])
        lines = """
        /* { dg-begin-multiline-output "" }
           { return foo + bar; }
                    ~~~~^~~~~
           { dg-end-multiline-output "" } */
        """
        for lineidx, line in enumerate(lines.splitlines()):
            directive = ctxt.parse_line(INPUT_FILE, lineidx + 1, line)
            if directive:
                ctxt.handle_directive(directive)

        self.assertEqual(len(ctxt.multiline_ranges), 1)
        mr = ctxt.multiline_ranges[0]
        self.assertEqual(mr.start, 3)
        self.assertEqual(mr.end, 4)
        self.assertEqual(mr.lines,
                         ['           { return foo + bar; }',
                          '                    ~~~~^~~~~'])

        stderr = ('           { return foo + bar; }\n'
                  + '                    ~~~~^~~~~\n')
        ctxt.check_result('', stderr, 0)
        self.assertEqual(ctxt.num_failures(), 0)

if __name__ == '__main__':
    unittest.main()
