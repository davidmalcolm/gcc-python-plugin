#   Copyright 2011, 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2011, 2012 Red Hat, Inc.
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

import gcc

from six.moves import xrange

def sorted_dict_repr(d):
    return '{' + ', '.join(['%r: %r' % (k, d[k])
                            for k in sorted(d.keys())]) + '}'

def get_src_for_loc(loc):
    # Given a gcc.Location, get the source line as a string
    import linecache
    return linecache.getline(loc.file, loc.line).rstrip()

def get_field_by_name(typeobj, name):
    check_isinstance(typeobj,
                     (gcc.RecordType, gcc.UnionType, gcc.QualUnionType))
    for field in typeobj.fields:
        if field.name == name:
            return field

def get_global_typedef(name):
    # Look up a typedef in global scope by name, returning a gcc.TypeDecl,
    # or None if not found
    for u in gcc.get_translation_units():
        if u.language == 'GNU C++':
            gns = gcc.get_global_namespace()
            return gns.lookup(name)
        if u.block:
            for v in u.block.vars:
                if isinstance(v, gcc.TypeDecl):
                    if v.name == name:
                        return v

def get_variables_as_dict():
    result = {}
    for var in gcc.get_variables():
        result[var.decl.name] = var
    return result

def get_global_vardecl_by_name(name):
    # Look up a variable in global scope by name, returning a gcc.VarDecl,
    # or None if not found
    for u in gcc.get_translation_units():
        if u.language == 'GNU C++':
            gns = gcc.get_global_namespace()
            return gns.lookup(name)
        for v in u.block.vars:
            if isinstance(v, gcc.VarDecl):
                if v.name == name:
                    return v

def get_nonnull_arguments(funtype):
    """
    'nonnull' is an attribute on the fun.decl.type

    http://gcc.gnu.org/onlinedocs/gcc/Function-Attributes.html

    It can either have no arguments (all pointer args are non-NULL), or
    be a list of integers.  These integers are 1-based.

    Return a frozenset of 0-based integers, giving the arguments for which we
    can assume the "nonnull" property.

    (Note the 0-based vs 1-based differences)

    Compare with gcc/tree-vrp.c: nonnull_arg_p
    """
    check_isinstance(funtype, (gcc.FunctionType, gcc.MethodType))
    if 'nonnull' in funtype.attributes:
        result = []
        nonnull = funtype.attributes['nonnull']
        if nonnull == []:
            # All pointer args are nonnull:
            for idx, parm in enumerate(funtype.argument_types):
                if isinstance(parm, gcc.PointerType):
                    result.append(idx)
        else:
            # Only the listed args are nonnull:
            for val in nonnull:
                check_isinstance(val, gcc.IntegerCst)
                result.append(val.constant - 1)
        return frozenset(result)
    else:
        # No "nonnull" attribute was given:
        return frozenset()

def invoke_dot(dot):
    from subprocess import Popen, PIPE

    if 1:
        fmt = 'png'
    else:
        # SVG generation seems to work, but am seeing some text-width issues
        # with rendering of the SVG  by eog and firefox on this machine (though
        # not chromium).
        #
        # Looks like X coordinates allocated by graphviz don't contain quite
        # enough space for the <text> elements.
        #
        # Presumably a font selection/font metrics issue
        fmt = 'svg'

    p = Popen(['dot', '-T%s' % fmt, '-o', 'test.%s' % fmt],
              stdin=PIPE)
    p.communicate(dot.encode('ascii'))

    p = Popen(['xdg-open', 'test.%s' % fmt])
    p.communicate()

def pprint(obj):
    pp = TextualPrettyPrinter()
    pp.pprint(obj)

def pformat(obj):
    pp = TextualPrettyPrinter()
    return pp.pformat(obj)


class PrettyPrinter(object):
    def __init__(self):
        self.show_addr = False

    def attr_to_str(self, name, value):
        if name == 'addr':
            return hex(value)
        if isinstance(value, str):
            return repr(value)
        return str(value)

    def iter_tree_attrs(self, obj):
        # Iterate through the interesting attributes of the object:
        for name in dir(obj):
            # Ignore private and "magic" attributes:
            if name.startswith('_'):
                continue
            value = getattr(obj, name)
            # Ignore methods:
            if hasattr(value, '__call__'):
                continue
            if not self.show_addr:
                if name == 'addr':
                    continue
            # Don't follow infinite chains, e.g.
            # ptr to ptr to ... of a type:
            if isinstance(obj, gcc.Type):
                if (name == 'pointer' or
                    name.endswith('equivalent')):
                    continue

            #print 'attr %r    obj.%s: %r' % (name, name, value)
            yield (name, value)


class TextualPrettyPrinter(PrettyPrinter):
    """Convert objects to nice textual dumps, loosely based on Python's pprint
    module"""
    def __init__(self):
        super(TextualPrettyPrinter, self).__init__()
        self.maxdepth = 5

    def pprint(self, obj):
        import sys
        sys.stdout.write(self.pformat(obj))

    def make_indent(self, indent):
        return indent * ' '

    def pformat(self, obj):
        return self._recursive_format_obj(obj, set(), 0)

    def indent(self, prefix, txt):
        return '\n'.join([prefix + line for line in txt.splitlines()])

    def _recursive_format_obj(self, obj, visited, depth):
        def str_for_kv(key, value):
            return '  %s = %s\n' % (key, value)

        check_isinstance(obj, gcc.Tree)
        visited.add(obj.addr)

        result = '<%s\n' % obj.__class__.__name__
        r = repr(obj)
        s = str(obj)
        result += str_for_kv('repr()', r)
        if s != r:
            result += str_for_kv('str()', '%r' % s)

        # Show MRO, stripping off this type from front and "object" from end:
        superclasses = obj.__class__.__mro__[1:-1]
        result += str_for_kv('superclasses',
                             superclasses)
        for name, value in self.iter_tree_attrs(obj):
            if depth < self.maxdepth:
                if isinstance(value, gcc.Tree):
                    if value.addr in visited:
                        result += str_for_kv('.%s' % name,
                                             '... (%s)' % self.attr_to_str(name, repr(value)))
                    else:
                        # Recurse
                        formatted_value = self._recursive_format_obj(value,
                                              visited, depth + 1)
                        indented_value = self.indent(' ' * (len(name) + 6),
                                                     formatted_value)
                        result += str_for_kv('.%s' % name,
                                             indented_value.lstrip())
                    continue
            # Otherwise: just print short version of the attribute:
            result += str_for_kv('.%s' % name,
                                 self.attr_to_str(name, value))

        result += '>\n'
        return result

class DotPrettyPrinter(PrettyPrinter):
    # Base class for various kinds of data visualizations that use graphviz
    # (aka ".dot" source files)
    def to_html(self, text):
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

    def _dot_td(self, text, align="left", colspan=1, escape=1, bgcolor=None,
                port=None):
        if escape:
            text = self.to_html(text)
        attribs = 'align="%s" colspan="%i"' % (align, colspan)
        if bgcolor:
            attribs += ' bgcolor="%s"' % bgcolor
        if port:
            attribs += ' port="%s"' % port
        return ('<td %s>%s</td>'
                % (attribs, text))

    def _dot_tr(self, td_text):
        return ('<tr>%s</tr>\n' % self._dot_td(td_text))

try:
    from pygments.formatter import Formatter
    from pygments.token import Token
    from pygments.styles import get_style_by_name

    class GraphvizHtmlFormatter(Formatter, DotPrettyPrinter):
        """
        A pygments Formatter to turn source code fragments into graphviz's
        pseudo-HTML format.
        """
        def __init__(self, style):
            Formatter.__init__(self)
            self.style = style

        def style_for_token(self, token):
            # Return a (hexcolor, isbold) pair, where hexcolor could be None

            # Lookup up pygments' color for this token type:
            col = self.style.styles[token]

            isbold = False

            # Extract a pure hex color specifier of the form that graphviz can
            # deal with
            if col:
                if col.startswith('bold '):
                    isbold = True
                    col = col[5:]
            return (col, isbold)

        def format_unencoded(self, tokensource, outfile):
            from pprint import pprint
            for t, piece in tokensource:
                # graphviz seems to choke on font elements with no inner text:
                if piece == '':
                    continue

                # pygments seems to add this:
                if piece == '\n':
                    continue

                # avoid croaking on '\n':
                if t == Token.Literal.String.Escape:
                    continue

                color, isbold = self.style_for_token(t)
                if 0:
                    print ('(color, isbold): (%r, %r)' % (color, isbold))

                if isbold:
                    outfile.write('<b>')

                # Avoid empty color="" values:
                if color:
                    outfile.write('<font color="%s">' % color
                                  + self.to_html(piece)
                                  + '</font>')
                else:
                    outfile.write(self.to_html(piece))

                if isbold:
                    outfile.write('</b>')

    from pygments import highlight
    from pygments.lexers import CLexer
    from pygments.formatters import HtmlFormatter

    def code_to_graphviz_html(code):
        style = get_style_by_name('default')
        return highlight(code,
                         CLexer(), # FIXME
                         GraphvizHtmlFormatter(style))

    using_pygments = True
except ImportError:
    using_pygments = False

class CfgPrettyPrinter(DotPrettyPrinter):
    # Generate graphviz source for this gcc.Cfg instance, as a string
    def __init__(self, cfg, name=None):
        self.cfg = cfg
        if name:
            self.name = name

    def block_id(self, b):
        if b is self.cfg.entry:
            return 'entry'
        if b is self.cfg.exit:
            return 'exit'
        return 'block%i' % id(b)

    def block_to_dot_label(self, bb):
        # FIXME: font setting appears to work on my machine, but I invented
        # the attribute value; it may be exercising a failure path
        result = '<font face="monospace"><table cellborder="0" border="0" cellspacing="0">\n'
        result += '<tr> <td>BLOCK %i</td> <td></td> </tr>\n' % bb.index
        curloc = None
        if isinstance(bb.phi_nodes, list):
            for stmtidx, phi in enumerate(bb.phi_nodes):
                result += '<tr><td></td>' + self.stmt_to_html(phi, stmtidx) + '</tr>\n'
        if isinstance(bb.gimple, list) and bb.gimple != []:
            for stmtidx, stmt in enumerate(bb.gimple):
                if curloc != stmt.loc:
                    curloc = stmt.loc
                    code = get_src_for_loc(stmt.loc).rstrip()
                    pseudohtml = self.code_to_html(code)
                    # print('pseudohtml: %r' % pseudohtml)
                    result += ('<tr><td align="left">'
                               + self.to_html('%4i ' % stmt.loc.line)
                               + pseudohtml
                               + '<br/>'
                               + (' ' * (5 + stmt.loc.column-1)) + '^'
                               + '</td></tr>')
                    
                result += '<tr><td></td>' + self.stmt_to_html(stmt, stmtidx) + '</tr>\n'
        else:
            # (prevent graphviz syntax error for empty blocks):
            result += self._dot_tr(self.block_id(bb))
        result += '</table></font>\n'
        return result

    def code_to_html(self, code):
        if using_pygments:
            return code_to_graphviz_html(code)
        else:
            return self.to_html(code)

    def stmt_to_html(self, stmt, stmtidx):
        text = str(stmt).strip()
        text = self.code_to_html(text)
        bgcolor = None

        # Work towards visualization of CPython refcounting rules.
        # For now, paint assignments to (PyObject*) vars and to ob_refcnt
        # fields, to highlight the areas needing tracking:
        # print 'stmt: %s' % stmt
        if 0: # hasattr(stmt, 'lhs'):
            # print 'stmt.lhs: %s' % stmt.lhs
            # print 'stmt.lhs: %r' % stmt.lhs
            if stmt.lhs:
                # print 'stmt.lhs.type: %s' % stmt.lhs.type

                # Color assignments to (PyObject *) in red:
                if str(stmt.lhs.type) == 'struct PyObject *':
                    bgcolor = 'red'

                # Color assignments to PTR->ob_refcnt in blue:
                if isinstance(stmt.lhs, gcc.ComponentRef):
                    # print(dir(stmt.lhs))
                    # print 'stmt.lhs.target: %s' % stmt.lhs.target
                    # print 'stmt.lhs.target.type: %s' % stmt.lhs.target.type
                    # (presumably we need to filter these to structs that are
                    # PyObject, or subclasses)
                    # print 'stmt.lhs.field: %s' % stmt.lhs.field
                    if stmt.lhs.field.name == 'ob_refcnt':
                        bgcolor = 'blue'

        return self._dot_td(text, escape=0, bgcolor=bgcolor, port='stmt%i' % stmtidx)

    def edge_to_dot(self, e):
        if e.true_value:
            attrliststr = '[label = true]'
        elif e.false_value:
            attrliststr = '[label = false]'
        elif e.loop_exit:
            attrliststr = '[label = loop_exit]'
        elif e.fallthru:
            attrliststr = '[label = fallthru]'
        elif e.dfs_back:
            attrliststr = '[label = dfs_back]'
        else:
            attrliststr = ''
        return ('   %s -> %s %s;\n'
                % (self.block_id(e.src), self.block_id(e.dest), attrliststr))

    def extra_items(self):
        # Hook for expansion
        return ''

    def to_dot(self):
        if hasattr(self, 'name'):
            name = self.name
        else:
            name = 'G'
        result = 'digraph %s {\n' % name
        result += ' subgraph cluster_cfg {\n'
        #result += '  label="CFG";\n'
        result += '  node [shape=box];\n'
        for block in self.cfg.basic_blocks:

            result += ('  %s [label=<%s>];\n'
                       % (self.block_id(block), self.block_to_dot_label(block)))

            for edge in block.succs:
                result += self.edge_to_dot(edge)
            # FIXME: this will have duplicates:
            #for edge in block.preds:
            #    result += edge_to_dot(edge)
        result += ' }\n'

        # Potentially add extra material:
        result += self.extra_items()
        result += '}\n'
        return result

class TreePrettyPrinter(DotPrettyPrinter):
    # Generate a graphviz visualization of this gcc.Tree and the graphs of
    # nodes it references, as a string
    def __init__(self, root):
        print('root: %s' % root)
        check_isinstance(root, gcc.Tree)
        self.root = root
        self.show_addr = False
        self.maxdepth = 6 # for now

    def tr_for_kv(self, key, value):
        return ('<tr> %s %s</tr>\n'
                % (self._dot_td(key),
                   self._dot_td(value)))

    def label_for_tree(self, obj):
        result = '<table cellborder="0" border="0" cellspacing="0">\n'
        r = repr(obj)
        s = str(obj)
        result += self.tr_for_kv('repr()', r)
        if s != r:
            result += self.tr_for_kv('str()', '%r' % s)

        # Show MRO, stripping off this type from front and "object" from end:
        superclasses = obj.__class__.__mro__[1:-1]
        result += self.tr_for_kv('superclasses',
                                 superclasses)

        for name, value in self.iter_tree_attrs(obj):
            result += ('<tr> %s %s </tr>\n'
                       % (self._dot_td(name),
                          self._dot_td(self.attr_to_str(name, value))))
        result += '</table>\n'
        return result

    def tree_id(self, obj):
        return 'id%s' % id(obj)

    def tree_to_dot(self, obj):
        check_isinstance(obj, gcc.Tree)
        return ('  %s [label=<%s>];\n'
                % (self.tree_id(obj), self.label_for_tree(obj)))

    def recursive_tree_to_dot(self, obj, visited, depth):
        print('recursive_tree_to_dot(%r, %r)' % (obj, visited))
        check_isinstance(obj, gcc.Tree)
        result = self.tree_to_dot(obj)
        visited.add(obj.addr)
        if depth < self.maxdepth:
            for name, value in self.iter_tree_attrs(obj):
                if isinstance(value, gcc.Tree):
                    if value.addr not in visited:
                        # Recurse
                        result += self.recursive_tree_to_dot(value,
                                                             visited, depth + 1)
                    # Add edge:
                    result += ('   %s -> %s [label = %s];\n'
                               % (self.tree_id(obj),
                                  self.tree_id(value),
                                  name))
        return result

    def to_dot(self):
        self.root.debug()
        result = 'digraph G {\n'
        result += '  node [shape=record];\n'
        result += self.recursive_tree_to_dot(self.root, set(), 0)
        result += '}\n'
        return result

def cfg_to_dot(cfg, name = None):
    pp = CfgPrettyPrinter(cfg, name)
    return pp.to_dot()


def tree_to_dot(tree):
    pp = TreePrettyPrinter(tree)
    return pp.to_dot()

class Table(object):
    '''A table of text/numbers that knows how to print itself'''
    def __init__(self, columnheadings=None, rows=[], sepchar='-'):
        self.numcolumns = len(columnheadings)
        self.columnheadings = columnheadings
        self.rows = []
        self._colsep = '  '
        self._sepchar = sepchar

    def add_row(self, row):
        assert len(row) == self.numcolumns
        self.rows.append(row)

    def write(self, out):
        colwidths = self._calc_col_widths()

        self._write_separator(out, colwidths)

        self._write_row(out, colwidths, self.columnheadings)

        self._write_separator(out, colwidths)

        for row in self.rows:
            self._write_row(out, colwidths, row)

        self._write_separator(out, colwidths)

    def _calc_col_widths(self):
        result = []
        for colIndex in xrange(self.numcolumns):
            result.append(self._calc_col_width(colIndex))
        return result

    def _calc_col_width(self, idx):
        cells = [str(row[idx]) for row in self.rows]
        heading = self.columnheadings[idx]
        return max([len(c) for c in (cells + [heading])])

    def _write_row(self, out, colwidths, values):
        for i, (value, width) in enumerate(zip(values, colwidths)):
            if i > 0:
                out.write(self._colsep)
            formatString = "%%-%ds" % width # to generate e.g. "%-20s"
            out.write(formatString % value)
        out.write('\n')

    def _write_separator(self, out, colwidths):
        for i, width in enumerate(colwidths):
            if i > 0:
                out.write(self._colsep)
            out.write(self._sepchar * width)
        out.write('\n')

class CallgraphPrettyPrinter(DotPrettyPrinter):
    def node_id(self, cgn):
        return 'cgn%i' % id(cgn)

    def node_to_dot_label(self, cgn):
        return str(cgn.decl.name)

    def edge_to_dot(self, e):
        attrliststr = ''
        return ('   %s -> %s %s;\n'
                % (self.node_id(e.caller),
                   self.node_id(e.callee),
                   attrliststr))

    def to_dot(self):
        result = 'digraph Callgraph {\n'
        #result += ' subgraph cluster_callgraph {\n'
        result += '  node [shape=box];\n'
        for cgn in gcc.get_callgraph_nodes():
            result += ('  %s [label=<%s>];\n'
                       % (self.node_id(cgn), self.node_to_dot_label(cgn)))
            for edge in cgn.callers:
                result += self.edge_to_dot(edge)
        #result += ' }\n'
        result += '}\n'
        return result

def callgraph_to_dot():
    pp = CallgraphPrettyPrinter()
    return pp.to_dot()

def check_isinstance(obj, types):
    """
    Like:
       assert isinstance(obj, types)
    but with better error messages
    """
    if not isinstance(obj, types):
        raise TypeError('%s / %r is not an instance of %s' % (obj, obj, types))

def sorted_callgraph():
    """
    Return the callgraph, in topologically-sorted order
    """
    return topological_sort(gcc.get_callgraph_nodes(),
                            get_srcs=lambda n: [edge.caller
                                                for edge in n.callers
                                                # Strip out recursive calls:
                                                if edge.caller != n],
                            get_dsts=lambda n: [edge.callee
                                                for edge in n.callees
                                                # Strip out recursive calls:
                                                if edge.callee != n])

def topological_sort(nodes, get_srcs, get_dsts):
    """
    Topological sort in O(n), based on depth-first traversal
    """
    result = []
    visited = set()
    debug = False
    def visit(n):
        if n not in visited:
            if debug:
                print('first visit to %s' % n.decl)
            visited.add(n)
            for m in get_srcs(n):
                visit(m)
            if debug:
                print('adding to result: %s' % n.decl)
            result.append(n)
        else:
            if debug:
                print('already visited %s' % n.decl)

    for n in nodes:
        if not get_dsts(n):
            visit(n)

    return result

