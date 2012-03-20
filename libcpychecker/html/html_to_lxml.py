#!/usr/bin/env python
"""transform html into lxml statements"""

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

def main():
    """entry point"""
    from lxml.html import parse

    from sys import argv, stdout

    tree = parse(argv[1])
    root = tree.getroot()

    stack = [ (0, root) ]
    indent = 0

    def newline():
        """write a newline"""
        stdout.write('\n' + '    ' * indent)

    while stack:
        indent, node = stack.pop()
        newline()

        if isinstance(node, basestring):
            stdout.write(node)
            continue

        try:
            stdout.write('E.%s(' % node.tag.upper())
        except:
            import pudb
            pudb.set_trace()
            raise

        indent += 1
        children = node.getchildren()
        attrs = node.attrib
        if 'class' in attrs:
            newline()
            stdout.write('E.CLASS(%r),' % attrs.pop('class'))

        if attrs:
            newline()
            if children or node.text:
                stdout.write('E.ATTR(')
            if any('-' in attr for attr in attrs):
                stdout.write('{')
                stdout.write(
                        ', '.join('%r: %r' % attr for attr in attrs.items())
                )
                stdout.write('}')
            else:
                stdout.write(
                        ', '.join('%s=%r' % attr for attr in attrs.items())
                )
            if children or node.text:
                stdout.write(')')
            stdout.write(',')

        if node.text:
            newline()
            stdout.write(repr(node.text))
            stdout.write(',')

        stack.append((indent-1, '),'))
        for child in reversed(children):
            if child.tail:
                stack.append((indent, repr(child.tail) + ','))
            stack.append((indent, child))

main()
