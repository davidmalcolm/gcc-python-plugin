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
 PRIORITY__REFERENCE_LEAK_OF_SINGLETON,
 PRIORITY__SEGFAULT_IN_ERROR_HANDLING,
 PRIORITY__REFERENCE_LEAK,
 PRIORITY__REFERENCE_COUNT_TOO_LOW,
 PRIORITY__SEGFAULT_IN_NORMAL_USE,
 PRIORITY__UNCLASSIFIED,
 ) = range(7)

class Triager:
    """
    Classify ErrorReport instances into various severity levels, identified by
    Severity instances
    """
    def _classify_segfault(self, report):
        if report.contains_failure():
            return Severity(priority=PRIORITY__SEGFAULT_IN_ERROR_HANDLING,
                            title='Segfaults within error-handling paths',
                            description='')
        else:
            return Severity(priority=PRIORITY__SEGFAULT_IN_NORMAL_USE,
                            title='Segfaults in normal paths',
                            description='')

    def classify(self, report):
        m = re.match('ob_refcnt of (.+) too high', report.errmsg)
        if m:
            if 'PyBool_FromLong' in report.errmsg:
                is_singleton = True
            else:
                is_singleton = False
            if is_singleton:
                return Severity(priority=PRIORITY__REFERENCE_LEAK_OF_SINGLETON,
                                title='Reference leaks of a singleton',
                                description=('Code paths in which the reference count of a singleton object will be left too large.  '
                                             'Technically incorrect, but unlikely to cause problems'))
            else:
                return Severity(priority=PRIORITY__REFERENCE_LEAK,
                                title='Reference leaks',
                                description='')

        m = re.match('ob_refcnt of (.+) too low', report.errmsg)
        if m:
            return Severity(priority=PRIORITY__REFERENCE_COUNT_TOO_LOW,
                            title='Reference count too low',
                            description='')

        if report.errmsg == 'returning (PyObject*)NULL without setting an exception':
            return Severity(priority=PRIORITY__RETURNING_NULL_WITHOUT_SETTING_EXCEPTION,
                            title='Returning (PyObject*)NULL without setting an exception',
                            description='These messages are often false-positives')

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
                        description="The triager didn't know how to classify these ones")

def gather_html_reports(path):
    outpath = os.path.join(path, 'index.html')
    with open(outpath, 'w') as f:
        f.write('<html><head><title>%s</title></head>\n' % path)
        f.write('  <body>\n')

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
                f.write('    <p>%s</p>\n' % sev.description)
                f.write('    <table>\n')
                for er in severities[sev]:
                    href = os.path.relpath(er.href(), path)
                    f.write('      <tr> <td><a href=%s>%s</a></td> <td><a href=%s>%s</a></td> <td><a href=%s>%s</a></td> </tr>'
                            % (href, er.filename,
                               href, er.function,
                               href, er.errmsg))
                f.write('    </table>\n')

        f.write('  </body>\n')
        f.write('</html>\n')


# locate .html
# iterate over toplevel in "LOGS":
for resultdir in os.listdir('LOGS'):
    resultpath = os.path.join('LOGS', resultdir)
    print(resultpath)
    gather_html_reports(resultpath)
