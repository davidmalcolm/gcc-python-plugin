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

# Walk a directory hierarchy looking for *-refcount-errors.html files,
# building an index.html linking to them all

from collections import namedtuple
import os
import re

from BeautifulSoup import BeautifulSoup

class ErrorReport(namedtuple('ErrorReport',
                             ('htmlpath', 'htmlid', 'filename', 'function', 'errmsg', 'htmlpre'))):
    def href(self):
        return '%s#%s' % (self.htmlpath, self.htmlid)

    def contains_failure(self):
        # Does this appear to be within an error-handling path?
        print('htmlpre: %s' % self.htmlpre)
        m = re.match('.*when (\S+) fails.*',
                     str(self.htmlpre),
                     re.MULTILINE|re.DOTALL)
        if m:
            print m.groups()
            return True
        else:
            print 'not matched'
            return False

    def is_within_initialization(self):
        # Does this appear to be within an initialization function?
        # (and thus called only once)
        htmlpre = str(self.htmlpre)

        # The following functions typically only appear in one-time
        # initialization code:
        initfns = (
            # there are various init functions with this prefix:
            'Py_InitModule',
            # Other init functions:
            'PyErr_NewException', 'PyType_Ready', 'PyCFunction_NewEx',
            'PyImport_ImportModule',
            )

        for fnname in initfns:
            if fnname in htmlpre:
                return True
        return False

    def might_be_borrowed_ref(self):
        htmlpre = str(self.htmlpre)

        if 'new ref from (unknown)' in htmlpre:
            # The reference that we're complaining about comes from
            # an unknown function, for which we assumed it was a new
            # ref - but it could be a borrowed ref, in which case it isn't
            # a problem
            return True

        if 'new ref from call through function pointer' in htmlpre:
            # Similar: we can't know the semantics of function pointers
            # in user-supplied code:
            return True

        return False

def get_errors_from_file(htmlpath):
    """
    Scrape metadata from out of a -refcount-errors.html file,
    yielding a sequence of ErrorReport
    """
    with open(htmlpath) as f:
        soup = BeautifulSoup(f)
        # Look within top-level <div> elements for result summaries that
        # look like this:
        #  <div id="report-0">
        #   <table>
        #     <tr><td>File:</td> <td><b>gstmodule.c</b></td></tr>
        #     <tr><td>Function:</td> <td><b>init_gst</b></td></tr>
        #     <tr><td>Error:</td> <td><b>ob_refcnt of new ref from (unknown) pygobject_init is 1 too high</b></td></tr>
        #   </table>
        for div in soup.html.body.findAll('div'):
            table = div.table
            if not table:
                continue
            print div['id']
            #print 'div: %r' % div
            rows = table('tr')
            def get_second_col(row):
                return row('td')[1].b.string
            # Capture the marked up source code and notes from the report:
            htmlpre = div.div.pre
            yield ErrorReport(htmlpath=htmlpath,
                              htmlid=div['id'],
                              filename=get_second_col(rows[0]),
                              function = get_second_col(rows[1]),
                              errmsg = get_second_col(rows[2]),
                              htmlpre = htmlpre)

class Severity(namedtuple('Severity', ('priority', 'title', 'description'))):
    """
    priority: the int values are in asending severity (so that e.g. priority 5
    is more severe than severity 4).  This should give us a useful sort order
    for Severity instances
    """

(PRIORITY__RETURNING_NULL_WITHOUT_SETTING_EXCEPTION,
 PRIORITY__POSSIBLE_REFERENCE_LEAK,
 PRIORITY__REFERENCE_LEAK_OF_SINGLETON,
 PRIORITY__SEGFAULT_IN_ERROR_HANDLING,
 PRIORITY__REFERENCE_LEAK_IN_INITIALIZATION,
 PRIORITY__REFERENCE_COUNT_TOO_LOW_IN_INITIALIZATION,
 PRIORITY__REFERENCE_LEAK_IN_NORMAL_USE,
 PRIORITY__REFERENCE_COUNT_TOO_LOW_IN_NORMAL_USE,
 PRIORITY__SEGFAULT_IN_NORMAL_USE,
 PRIORITY__UNCLASSIFIED,
 ) = range(10)

class Triager:
    """
    Classify ErrorReport instances into various severity levels, identified by
    Severity instances
    """
    def _classify_segfault(self, report):
        if report.contains_failure():
            return Severity(priority=PRIORITY__SEGFAULT_IN_ERROR_HANDLING,
                            title='Segfaults within error-handling paths',
                            description='<p>Code paths in error-handling that will lead to a segmentatation fault (e.g. under low memory conditions)</p>')
        else:
            return Severity(priority=PRIORITY__SEGFAULT_IN_NORMAL_USE,
                            title='Segfaults in normal paths',
                            description='<p>Code paths that will lead to a segmentatation fault</p>')

    def classify(self, report):
        m = re.match('ob_refcnt of (.+) too high', report.errmsg)
        if m:
            if report.might_be_borrowed_ref():
                return Severity(priority=PRIORITY__POSSIBLE_REFERENCE_LEAK,
                                title='Possible reference leaks',
                                description=("""
<p>Code paths in which the reference count of an object might too large - but in
which the reference in question came from a function not known to the
analyzer.</p>

<p>The analyzer assumes such references are new references, but if the function
returns a borrowed reference instead, it's probably not a bug</p>"""
                                             ))
            if 'PyBool_FromLong' in report.errmsg:
                is_singleton = True
            else:
                is_singleton = False
            if is_singleton:
                return Severity(priority=PRIORITY__REFERENCE_LEAK_OF_SINGLETON,
                                title='Reference leaks of a singleton',
                                description=('''
<p>Code paths in which the reference count of a singleton object will be
left too large.</p>

<p>Technically incorrect, but unlikely to cause problems</p>
'''
                                             ))
            else:
                if report.is_within_initialization():
                    return Severity(priority=PRIORITY__REFERENCE_LEAK_IN_INITIALIZATION,
                                    title='Reference leak within initialization',
                                    description='''
<p>Code paths in which the reference count of an object is left too high,
but within an initialization routine, and thus likely to only happen
once</p>''')
                else:
                    return Severity(priority=PRIORITY__REFERENCE_LEAK_IN_NORMAL_USE,
                                    title='Reference leaks',
                                    description='''
<p>Code paths in which the reference count of an object is left too high,
leading to memory leaks</p>''')
        m = re.match('ob_refcnt of (.+) too low', report.errmsg)
        if m:
            if report.is_within_initialization():
                return Severity(priority=PRIORITY__REFERENCE_COUNT_TOO_LOW_IN_INITIALIZATION,
                                title='Reference count too low within an initialization routine',
                                description='''
<p>Code paths in which the reference count of an object is too low, but
within an initialization routine, and thus likely to only happen once</p>
'''
                                )
            else:
                return Severity(priority=PRIORITY__REFERENCE_COUNT_TOO_LOW_IN_NORMAL_USE,
                                title='Reference count too low',
                                description='''
<p>Code paths in which the reference count of an object is left too low.
This could lead to the object being deallocated too early, triggering
segfaults when later accessed.   Over repeated calls, these errors could
accumulate, increasing the likelihood of a segfault.</p>''')

        if report.errmsg == 'returning (PyObject*)NULL without setting an exception':
            return Severity(priority=PRIORITY__RETURNING_NULL_WITHOUT_SETTING_EXCEPTION,
                            title='Returning (PyObject*)NULL without setting an exception',
                            description='''
<p>These messages are often false-positives: the analysis tool has no knowledge
about internal API calls that can lead to an exception being set''')

        m = re.match('calling (.+) with NULL as argument (.*)', report.errmsg)
        if m:
            return self._classify_segfault(report)

        m = re.match('dereferencing NULL (.*)', report.errmsg)
        if m:
            return self._classify_segfault(report)

        m = re.match('reading from deallocated memory (.*)', report.errmsg)
        if m:
            return self._classify_segfault(report)

        return Severity(priority=PRIORITY__UNCLASSIFIED,
                        title='Unclassified errors',
                        description='''
<p>The triager didn't know how to classify these ones</p>
''')

class BuildLog:
    # Wrapper around a "build.log" scraped from the mock build
    def __init__(self, path):
        self.seen_plugin = False
        self.unimplemented_functions = set()

        buildlog = os.path.join(path, 'build.log')
        with open(buildlog) as f:
            for line in f.readlines():
                if 0:
                    print repr(line)
                if '-fplugin=python2 -fplugin-arg-python2-script=/test.py' in line:
                    self.seen_plugin = True
                m = re.match('NotImplementedError: not yet implemented: (\S+)',
                             line)
                if m:
                    self.unimplemented_functions.add(m.group(1))

def generate_index_html(path, title):
    outpath = os.path.join(path, 'index.html')
    with open(outpath, 'w') as f:
        f.write('<html><head><title>%s</title></head>\n' % title)
        f.write('  <body>\n')

        f.write('  <h1>%s</h1>\n' % title)
        f.write("  <p>This is a summary of errors seen when compiling with <a href='https://fedorahosted.org/gcc-python-plugin/'>an experimental static analysis tool</a></p>")
        f.write('  <p>Raw build logs can be seen <a href="build.log">here</a></p>\n')

        buildlog = BuildLog(path)
        if not buildlog.seen_plugin:
            f.write('    <p>The GCC arguments for invoking the plugin were\n'
                    '       not seen in the build logs: did the plugin actually\n'
                    '       get run?</p>')

        # Gather the ErrorReport by severity
        triager = Triager()

        # mapping from Severity to list of ErrorReport
        severities = {}

        for dirpath, dirnames, filenames in os.walk(path):
            #print dirpath, dirnames, filenames
            for filename in filenames:
                if filename.endswith('-refcount-errors.html'):
                    print '  ', os.path.join(dirpath, filename)
                    htmlpath = os.path.join(dirpath, filename)
                    for er in get_errors_from_file(htmlpath):
                        print(er.filename)
                        print(er.function)
                        print(er.errmsg)
                        sev = triager.classify(er)
                        print(sev)
                        if sev in severities:
                            severities[sev].append(er)
                        else:
                            severities[sev] = [er]

            for sev in sorted(severities.keys())[::-1]:
                f.write('    <h2>%s</h2>\n' % sev.title)
                f.write('    %s\n' % sev.description)
                f.write('    <table>\n')
                for er in severities[sev]:
                    href = os.path.relpath(er.href(), path)
                    f.write('      <tr> <td><a href=%s>%s</a></td> <td><a href=%s>%s</a></td> <td><a href=%s>%s</a></td> </tr>'
                            % (href, er.filename,
                               href, er.function,
                               href, er.errmsg))
                f.write('    </table>\n')

        if buildlog.unimplemented_functions:
            f.write('    <h2>Implementation notes for gcc-with-cpychecker</h2>\n')
            f.write('    <p>The following "Py" functions were used but aren\'t\n'
                    '       yet explicitly handled by gcc-with-cpychecker</p>\n'
                    '    <ul>\n')
            for fnname in sorted(buildlog.unimplemented_functions):
                f.write('      <li><pre>%s</pre></li>\n' % fnname)
            f.write('    </ul>\n')

        f.write('  </body>\n')
        f.write('</html>\n')

def main():
    # locate .html
    # iterate over toplevel in "LOGS":
    for resultdir in os.listdir('LOGS'):
        resultpath = os.path.join('LOGS', resultdir)
        print(resultpath)
        generate_index_html(resultpath, 'Errors seen in %s' % resultdir)

if __name__ == '__main__':
    main()

