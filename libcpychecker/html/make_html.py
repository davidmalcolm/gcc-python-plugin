#!/usr/bin/env python2
"""Make our data into HTML!"""

import capi

from lxml.html import (
        tostring, fragment_fromstring as parse, builder as E
)

from pygments import highlight
from pygments.lexers.compiled import CLexer
from pygments.formatters.html import HtmlFormatter

import copy
import itertools
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
            for js in ('extlib/prefixfree-1.0.4.min', 'extlib/jquery-1.7.1.min', 'script')
        )
        return head

    def raw_code(self):
        first, last = self.data['function']['lines']
        # Line numbers are ONE-based
        return ''.join(itertools.islice(self.codefile, first - 1, last))

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
        def report_links():
            for i in range(len(self.data['reports'])):
                yield E.A(str(i + 1), href="#state{0}".format(i + 1))

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
                    *report_links()
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
            E.P(
                u'Hackathon 7.0 | '
                u'Buck G, Alex M, Jason M | '
                u'Yelp HQ 2012',
            ),
        )

    def states(self):
        for report in self.data['reports']:
            lis = []
            last_line = None
            for state in report['states']:
                if not state['location'] or not state['message']:
                    continue

                line = state['location'][0]['line']
                p = E.P(state['message'])
                p.append(
                                E.IMG(
                                    src='images/bug--arrow.png', align='center',
                                ),
                            )

                if lis and line == last_line:
                    # Merge adjacent messages for the same line together
                    lis[-1].append(p)
                else:
                    lis.append(E.LI(
                        {'data-line': str(line)},
                        p,
                    ))

                last_line = line

            final_li = E.LI({'data-line': str(self.data['function']['lines'][-1] - 1)})
            for note in report['notes']:
                final_li.append(
                    E.P(note['message']),
                )
            lis.append(final_li)

            html = E.OL(
                {'class': 'states'},
                *lis
            )

            yield html, report['message']

    def body(self):
        """The BODY of the html document"""
        reports = []
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
                        copy.deepcopy(code),
                    ),
                    state_html,
                ),
            )

        return E.BODY(
            self.header(),
            E.OL(
                E.ATTR(id='reports'),
                *reports
            ),
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
    print HtmlPage(codefile, jsonfile)

if __name__ == '__main__':
    from sys import argv as ARGV
    exit(main(ARGV))
