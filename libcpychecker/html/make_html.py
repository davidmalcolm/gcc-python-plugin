#!/usr/bin/env python
"""Make our data into HTML!"""

from lxml.html import (
        tostring, fragment_fromstring as parse, builder as E
)
from json import load

from pygments import highlight
from pygments.lexers.compiled import CLexer
from pygments.formatters.html import HtmlFormatter

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

    @staticmethod
    def head():
        """The HEAD of the html document"""
        head =  E.HEAD()
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
        return parse(highlight(self.codefile.read(), CLexer(), formatter))

    def body(self):
        """The BODY of the html document"""
        return E.BODY(
                E.DIV(
                    E.ATTR(id='main'),
                    E.DIV(self.code(), id='code'),
                    E.DIV(id='notes'),
                )
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
