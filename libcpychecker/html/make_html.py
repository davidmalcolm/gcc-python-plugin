#!/usr/bin/env python
"""Make our data into HTML!"""

import capi

from lxml.html import (
        tostring, fragment_fromstring as parse, builder as E
)

from pygments import highlight
from pygments.lexers.compiled import CLexer
from pygments.formatters.html import HtmlFormatter

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
                    '[Report Pagination]',
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
                        src='images/arrow.png',
                    ),
                ),
                E.DIV(
                    E.ATTR(id='next'),
                    E.IMG(
                        src='images/arrow-180.png',
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
        report = self.data['reports'][0]

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

        return E.OL(
            {'class': 'states'},
            *lis
        )

    def body(self):
        """The BODY of the html document"""
        return E.BODY(
            self.header(),
            E.OL(
                E.ATTR(id='reports'),
                E.LI(
                    E.DIV(
                        E.CLASS('source'),
                        E.DIV(
                            E.ATTR(id='error-box'),
                            E.SPAN(
                                E.CLASS('label'),
                                'Error: ',
                            ),
                            ' [error type]',
                        ),
                        E.DIV(
                            E.ATTR(id='report-count'),
                            E.SPAN(
                                E.CLASS('label'),
                                'Report: ',
                            ),
                            ' [count]',
                        ),
                        self.code(),
                        E.DIV(
                            E.CLASS('hr'),
                            E.HR(),
                        ),
                    ),
                    self.states(),
                ),
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
        
    def wrap2(self, source, outfile):
        """not used"""
        return super(CodeHtmlFormatter, self).wrap(source, outfile)

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
