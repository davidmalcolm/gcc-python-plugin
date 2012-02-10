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

from BeautifulSoup import BeautifulSoup

class ErrorReport(namedtuple('ErrorReport',
                             ('filename', 'function', 'errmsg'))):
    pass

def get_errors_from_file(path):
    """
    Scrape metadata from out of a -refcount-errors.html file,
    yielding a sequence of ErrorReport
    """
    with open(path) as f:
        soup = BeautifulSoup(f)
        # Look within top-level <table> elements for result summaries that
        # look like this:
        #   <table>
        #     <tr><td>File:</td> <td><b>gstmodule.c</b></td></tr>
        #     <tr><td>Function:</td> <td><b>init_gst</b></td></tr>
        #     <tr><td>Error:</td> <td><b>ob_refcnt of new ref from (unknown) pygobject_init is 1 too high</b></td></tr>
        #   </table>
        for table in soup.html.body.findAll('table'):
            rows = table('tr')
            def get_second_col(row):
                return row('td')[1].b.string
            yield ErrorReport(filename=get_second_col(rows[0]),
                              function = get_second_col(rows[1]),
                              errmsg = get_second_col(rows[2]))

def gather_html_reports(path):
    outpath = os.path.join(path, 'index.html')
    with open(outpath, 'w') as f:
        f.write('<html><head><title>%s</title></head>\n' % path)
        f.write('  <body>\n')
        f.write('    <table>\n')

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
                        href = os.path.relpath(htmlpath, path)
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
