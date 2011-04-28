def get_src_for_loc(loc):
    # Given a gcc.Location, get the source line as a string
    import linecache
    return linecache.getline(loc.file, loc.line).rstrip()

def invoke_dot(dot):
    from subprocess import Popen, PIPE
    p = Popen(['dot', '-Tpng', '-o', 'test.png'],
              stdin=PIPE)
    p.communicate(dot)

    p = Popen(['eog', 'test.png'])
    p.communicate()
    

def cfg_to_dot(cfg):
    # Generate graphviz source for this gcc.Cfg instance, as a string

    def to_html(self):
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
            
            # 'dot' doesn't seem to like these:
            '{': '\\{',
            '}': '\\}',
          }
        return "".join(html_escape_table.get(c,c) for c in str(self))

    def block_id(b):
        if b is cfg.entry:
            return 'entry'
        if b is cfg.exit:
            return 'exit'
        return 'block%i' % id(b)

    def _dot_td(text, align="left", colspan=1):
        return ('<td align="%s" colspan="%i">%s</td>'
                % (align, colspan, to_html(text)))

    def _dot_tr(td_text):
        return ('<tr>%s</tr>\n' % _dot_td(td_text))

    def block_to_dot_label(bb):
        # FIXME: font setting appears to work on my machine, but I invented
        # the attribute value; it may be exercising a failure path
        result = '<font face="monospace"><table cellborder="0" border="0" cellspacing="0">\n'
        curloc = None
        if isinstance(bb.gimple, list):
            for stmt in bb.gimple:
                if curloc != stmt.loc:
                    curloc = stmt.loc
                    result += ('<tr><td>' + to_html(get_src_for_loc(stmt.loc))
                               + '<br/>'
                               + (' ' * (stmt.loc.column-1)) + '^'
                               + '</td></tr>')
                    
                result += '<tr><td></td>' + _dot_td(str(stmt).strip()) + '</tr>'
        else:
            result += _dot_tr(block_id(bb))
        result += '</table></font>\n'
        return result

    def edge_to_dot(e):
        return ('   %s -> %s;\n'
                % (block_id(e.src), block_id(e.dest)))
        
    result = 'digraph G {\n'
    result += '  node [shape=record];\n'
    for block in cfg.basic_blocks:

        result += ('  %s [label=<%s>];\n'
                   % (block_id(block), block_to_dot_label(block)))

        for edge in block.succs:
            result += edge_to_dot(edge)
        # FIXME: this will have duplicates:
        #for edge in block.preds:
        #    result += edge_to_dot(edge)

    result += '}\n'
    return result
