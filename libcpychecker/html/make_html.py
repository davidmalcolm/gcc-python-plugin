#!/usr/bin/env python
"""Make our data into HTML!"""

import capi

from lxml.html import (
        tostring, fragment_fromstring as parse, builder as E
)

from pygments import highlight
from pygments.lexers.compiled import CLexer
from pygments.formatters.html import HtmlFormatter

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
            for js in ('extlib/prefixfree-1.0.4.min', 'extlib/jquery-1.7.1.min')
        )
        return head

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
        code =  parse(highlight(self.codefile.read(), CLexer(), formatter))

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
        return E.DIV(
            E.ATTR(id='header-wrap'),
            E.DIV(
                E.ATTR(id='header-container'),
                E.DIV(
                    E.ATTR(id='header'),
                    E.H1(
                        'GCC Python Plugin',
                    ),
                    E.DIV(
                        E.ATTR(id='header-filename'),
                        E.SPAN(
                            E.CLASS('label'),
                            'Filename: ',
                        ),
                        self.data['filename'],
                    ),
                ),
            ),
            E.DIV(
                E.ATTR(id='nav-container'),
                E.DIV(
                    E.ATTR(id='nav'),
                    E.SPAN(
                        E.CLASS('label'),
                        'Function Name: ',
                    ),
                    E.SPAN(
                        E.CLASS('fnc-report'),
                        E.ATTR(id='fnc-name'),
                        '[Function name goes here]',
                    ),
                    u'\xa0|\xa0',
                    E.SPAN(
                        E.CLASS('label'),
                        'Report: ',
                    ),
                    E.SPAN(
                        E.CLASS('fnc-report'),
                        E.ATTR(id='report-pagination'),
                        '[Report Pagination]',
                    ),
                    E.DIV(
                        E.ATTR(id='white-box'),
                        E.IMG(
                            src='images/arrow.png',
                        ),
                    ),
                    E.DIV(
                        E.ATTR(id='white-box'),
                        E.IMG(
                            src='images/arrow-180.png',
                        ),
                    ),
                    E.DIV(
                        E.ATTR(id='bug-toggle'),
                        E.IMG(
                            src='images/bug.png',
                        ),
                        E.SPAN(
                            E.CLASS('label'),
                            'Bug: ',
                        ),
                        ' [count]',
                    ),
                ),
            ),
    )

    @staticmethod
    def footer():
        """make the footer"""
        return E.DIV(
                E.ATTR(id='footer-wrap'),
                E.DIV(
                    E.ATTR(id='footer-container'),
                    E.DIV(
                        E.ATTR(id='footer'),
                        E.DIV(
                            E.ATTR(id='footer-text'),
                            u'Hackathon 7.0 \xa0|\xa0 '
                            u'Buck G, Alex M, Jason M \xa0|\xa0 '
                            u'Yelp HQ 2012',
                        ),
                    ),
                ),
        )

    def body(self):
        """The BODY of the html document"""
        return E.BODY(
            self.header(),
            E.DIV(
                E.ATTR(id='ie6-container-wrap'),
                E.DIV(
                    E.ATTR(id='container'),
                    E.DIV(
                        E.ATTR(id='content'),
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
                    E.DIV(
                        E.ATTR(id='sidebar'),
                        E.DIV(
                            E.CLASS('annotation-box'),
                            E.IMG(
                                src='images/bug--arrow.png', align='center',
                            ),
                            ' : ',
                            E.SPAN(
                                E.CLASS('bug-count'),
                                '[bug count]',
                            ),
                            E.DIV(
                                E.CLASS('annotation-comment'),
                                'when PyArg_ParseTuple() succeeds ',
                                E.BR(),
                                ' taking False path',
                            ),
                        ),
                        E.DIV(
                            E.CLASS('annotation-box selected'),
                            E.IMG(
                                src='images/bug--arrow.png', align='center',
                            ),
                            ' : ',
                            E.SPAN(
                                E.CLASS('bug-count'),
                                '[bug count]',
                            ),
                            E.DIV(
                                E.CLASS('annotation-comment'),
                                'when PyArg_ParseTuple() succeeds ',
                                E.BR(),
                                ' taking False path',
                            ),
                        ),
                    ),
                ),
            ),
            self.footer(),
        )

class CodeHtmlFormatter(HtmlFormatter):
    """Format our HTML!"""

    def wrap(self, source, outfile):
        yield 0, '<table class="%s" data-first-line="%s">' % (
                self.cssclass, self.linenostart,
        )
        for i, line in source:
            if i == 1:
                # it's a line of formatted code
                yield 0, '<tr><td>'
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
