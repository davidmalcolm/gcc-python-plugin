#!/usr/bin/env python
"""Make our data into HTML!"""

from lxml.html import tostring, builder as E

class HtmlPage(object):
    """Represent one html page."""
    def __init__(self, data):
        self.data = data

    def __str__(self):
        html = tostring(self.__html__(), pretty_print=True)
        return '<!DOCTYPE html>\n' + html

    def __html__(self):
        return E.HTML( self.head(), self.body() )

    @staticmethod
    def head():
        """The HEAD of the html document"""
        return E.HEAD(
                E.LINK(rel='stylesheet', href='style.css', type='text/css'),
                E.SCRIPT(src='extlib/prefixfree-1.0.4.min.js'),
                E.SCRIPT(src='extlib/jquery-1.7.1.min.js'),
        )

    @staticmethod
    def body():
        """The BODY of the html document"""
        return E.BODY(
                E.DIV(
                    E.ATTR(id='main'),
                    E.DIV(id='code'),
                    E.DIV(id='notes'),
                )
        )


if __name__ == '__main__':
    print HtmlPage(None)
