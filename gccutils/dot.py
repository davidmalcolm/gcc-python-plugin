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

def to_html(text):
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",

        # 'dot' doesn't seem to like these:
        '{': '&#123;',
        '}': '&#125;',

        ']': '&#93;',
      }
    return "".join(html_escape_table.get(c,c) for c in str(text))


# An easy way to construct graphviz' pseudo-html:
class Node:
    def to_html(self):
        raise NotImplementedError()

class Element(Node):
    def __init__(self, children=None, **kwargs):
        if children is None:
            children = []
        else:
            assert isinstance(children, list)
        self.children = children
        self.attrs = kwargs

    def to_html(self):
        if self.attrs:
            attrstr = ''.join(' %s="%s"' % (attr, value)
                              for attr, value in self.attrs.items())
        else:
            attrstr = ''
        result = '<%s%s>' % (self.name, attrstr)
        for child in self.children:
            result += child.to_html()
        result += '</%s>' % self.name
        return result

    def add_child(self, child):
        self.children.append(child)
        return child

class Table(Element):
    def to_html(self):
        result = '<table cellborder="0" border="0" cellspacing="0">\n'
        for row in self.children:
            result += row.to_html()
        result += '</table>'
        return result

class Tr(Element):
    name = 'tr'

class Td(Element):
    name = 'td'

class Text(Node):
    def __init__(self, text):
        self.text = text

    def to_html(self):
        return to_html(self.text)

class Br(Element):
    def to_html(self):
        return '<br/>'

class Font(Element):
    name = 'font'
