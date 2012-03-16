#!/usr/bin/env python
"""transform html into lxml statements"""

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
