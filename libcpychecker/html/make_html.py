#!/usr/bin/env python
"""Make our data into HTML!"""

#   Copyright 2012 Buck Golemon <buck@yelp.com>
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

import capi

from lxml.html import (
        tostring, fragment_fromstring as parse, builder as E
)

from pygments import highlight
from pygments.lexers.compiled import CLexer
from pygments.formatters.html import HtmlFormatter

from copy import deepcopy
from itertools import islice
from json import load

class HtmlPage(object):
    """Represent one html page."""
    def __init__(self, codefile, jsonfile):
        self.codefile = codefile
        self.data = load(jsonfile)

    def __str__(self):
        html = tostring(self.__html__())
        return '<!DOCTYPE html>\n' + html

    def __html__(self):
        return E.HTML( self.head(), self.body() )

    def head(self):
        """The HEAD of the html document"""
        head =  E.HEAD(
            E.META({
                'http-equiv': 'Content-Type',
                'content': 'text/html; charset=utf-8'
            }),
            E.TITLE('%s -- GCC Python Plugin' % self.data['filename']),
        )
        head.extend(
            E.LINK(rel='stylesheet', href=css + '.css', type='text/css')
            for css in ('extlib/reset-20110126', 'pygments_c', 'style')
        )
        head.extend(
            E.SCRIPT(src=js + '.js')
            for js in (
                'extlib/prefixfree-1.0.4.min',
                'extlib/jquery-1.7.1.min',
                'script'
            )
        )
        return head

    def raw_code(self):
        """Get the correct lines from the code file"""
        first, last = self.data['function']['lines']
        # Line numbers are ONE-based
        return ''.join(islice(self.codefile, first - 1, last))

    def code(self):
        """generate the contents of the #code section"""
        # Get ready to use Pygments:
        formatter = CodeHtmlFormatter(
                style='default',
                cssclass='source',
                linenostart=self.data['function']['lines'][0],
        )

        #<link rel="stylesheet", href="pygments_c.css", type="text/css">
        open('pygments_c.css', 'w').write(formatter.get_style_defs())

        # Use pygments to convert it all to HTML:
        code =  parse(highlight(self.raw_code(), CLexer(), formatter))

        # linkify the python C-API functions
        for name in code.xpath('//span[@class="n"]'):
            url = capi.get_url(name.text)
            if url is not None:
                link = E.A(name.text, href=url)
                name.text = None
                name.append(link)

        return code


    def header(self):
        """Make the header bar of the webpage"""

        return E.E.header(
            E.ATTR(id='header'),
            E.DIV(
                E.ATTR(id='title'),
                E.H1(
                    'GCC Python Plugin',
                ),
                E.DIV(
                    E.ATTR(id='filename'),
                    E.SPAN(
                        E.CLASS('label'),
                        'Filename: ',
                    ),
                    self.data['filename'],
                ),
            ),
            E.E.nav(
                E.ATTR(id='nav'),
                E.DIV(
                    E.ATTR(id='function'),
                    E.H3('Function'),
                    self.data['function']['name'],
                ),
                E.DIV(
                    E.ATTR(id='report-pagination'),
                    E.H3('Report'),
                    *(
                        E.A(str(i + 1), href="#state{0}".format(i + 1))
                        for i in range(len(self.data['reports']))
                    )
                ),
                E.DIV(
                    E.ATTR(id='bug-toggle'),
                    E.IMG(
                        src='images/bug.png',
                    ),
                    E.H3('Bug'),
                    ' [count]',
                ),
                E.DIV(
                    E.ATTR(id='prev'),
                    E.IMG(
                        src='images/arrow-180.png',
                    ),
                ),
                E.DIV(
                    E.ATTR(id='next'),
                    E.IMG(
                        src='images/arrow.png',
                    ),
                ),
            ),
    )

    @staticmethod
    def footer():
        """make the footer"""
        return E.E.footer(
            E.ATTR(id='footer'),
            E.P(' &nbsp;|&nbsp; '.join((
                'Hackathon 7.0',
                'Buck G, Alex M, Jason M',
                'Yelp HQ 2012',
            )))
        )

    def states(self):
        """Return an ordered-list of states, for each report."""
        for report in self.data['reports']:
            annotations = E.OL({'class': 'states'})

            prevline = None
            lineno_to_index = {}
            index = -1
            for state in report['states']:
                if not state['location'] or not state['message']:
                    continue

                line = state['location'][0]['line']
                state = E.P(state['message'])

                # We try to combine with the previous state.
                if line != prevline:
                    child = E.LI({'data-line': str(line)})
                    annotations.append(child)
                    index += 1

                child.append(state)

                lineno_to_index[line] = (index, child)
                prevline = line

            for note in report['notes']:
                line = note['location'][0]['line']
                note = E.P({'class':'note'}, note['message'])

                # Put this note on the last matching state, if possible
                for ann in reversed(tuple(annotations)):
                    annline = int(ann.attrib['data-line'])
                    if line == annline:
                        ann.append(note)
                        break
                    elif line > annline:
                        ann.addnext(
                                E.LI({'data-line': str(line)}, note)
                        )
                        break
                else:
                    annotations.insert(0, 
                            E.LI({'data-line': str(line)}, note)
                    )

            yield annotations, report['message']

    def body(self):
        """The BODY of the html document"""
        reports = E.OL(id='reports')
        code = self.code()

        for i, (state_html, state_problem) in enumerate(self.states(), 1):
            reports.append(
                    E.LI(
                        E.ATTR(id="state{0}".format(i)),
                        E.DIV(
                            E.CLASS('source'),
                            E.E.header(
                                E.DIV(
                                    E.CLASS('error'),
                                    state_problem,
                                ),
                                E.DIV(
                                    E.CLASS('report-count'),
                                    E.H3('Report'),
                                    str(i),
                                ),
                            ),
                            deepcopy(code),
                        ),
                        state_html,
                    ),
            )

        return E.BODY(
            self.header(),
            reports,
            self.footer(),
        )

class CodeHtmlFormatter(HtmlFormatter):
    """Format our HTML!"""

    def wrap(self, source, outfile):
        yield 0, '<table data-first-line="%s">' % (
                self.linenostart,
        )
        for i, line in source:
            if i == 1:
                # it's a line of formatted code
                yield 0, '<tr><td class="code">'
                yield i, line
                yield 0, '</td></tr>'
            else:
                yield i, line
        yield 0, '</table>'

def main(argv):
    """our entry point"""
    if len(argv) < 3:
        return "Please provide code and json filenames."
    codefile = open(argv[1])
    jsonfile = open(argv[2])
    print(HtmlPage(codefile, jsonfile))

if __name__ == '__main__':
    from sys import argv as ARGV
    exit(main(ARGV))
