# Sample python script, to be run by our gcc plugin (see "make test")
#print "hello world"

import gcc

#import sys
#print 'sys.path:', sys.path
#help(gcc)

def get_src_for_loc(loc):
    # Given a gcc.Location, get the source line as a string
    import linecache
    return linecache.getline(loc.file, loc.line).rstrip()

def my_pass_execution_callback(*args, **kwargs):
    print('my_pass_execution_callback was called: args=%r  kwargs=%r' % (args, kwargs))
    #help(args[0])
    (optpass, fun) = args
    print 'optpass: %r' % optpass
    print 'fun: %r' % fun
    if fun:
        print 'fun.cfg: %r' % fun.cfg
        if fun.cfg:
            #print help(fun.cfg)
            print 'fun.cfg.basic_blocks: %r' % fun.cfg.basic_blocks
            print 'fun.cfg.entry: %r' % fun.cfg.entry
            print 'fun.cfg.exit: %r' % fun.cfg.exit
            print 'fun.cfg.entry.succs: %r' % fun.cfg.entry.succs
            print 'fun.cfg.exit.preds: %r' % fun.cfg.exit.preds
            
            dot = cfg_to_dot(fun.cfg)
            print dot
            invoke_dot(dot)
            for bb in fun.cfg.basic_blocks:
                print 'bb: %r' % bb
                print 'bb.gimple: %r' % bb.gimple
                if isinstance(bb.gimple, list):
                    for stmt in bb.gimple:
                        print '  %r: %r : %s column: %i block: %r' % (stmt, repr(str(stmt)), stmt.loc, stmt.loc.column, stmt.block)
                        print get_src_for_loc(stmt.loc)
                        print ' ' * (stmt.loc.column-1) + '^'
                        if hasattr(stmt, 'loc'):
                            print '      stmt.loc: %r' % stmt.loc
                        if hasattr(stmt, 'lhs'):
                            print '      stmt.lhs: %r' % stmt.lhs
                        if hasattr(stmt, 'exprtype'):
                            print '      stmt.exprtype: %r' % stmt.exprtype
                        if hasattr(stmt, 'exprcode'):
                            print '      stmt.exprcode: %r' % stmt.exprcode
                        if hasattr(stmt, 'fn'):
                            print '      stmt.fn: %r %s' % (stmt.fn, stmt.fn)
                        if hasattr(stmt, 'retval'):
                            print '      stmt.retval: %r' % stmt.retval
                        if hasattr(stmt, 'rhs'):
                            print '      stmt.rhs: %r' % stmt.rhs

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

    

def my_pre_genericize_callback(*args, **kwargs):
    print('my_pre_genericize_callback was called: args=%r  kwargs=%r' % (args, kwargs))
    #help(args[0])
    t = args[0]
    print(t)
    print(dir(t))
    print(type(t))
    print(repr(t))
    print(str(t))
    #print(help(t))

    print 't.name: %r' % t.name
    print 't.addr: %s' % hex(t.addr)
    print 't.type: %r' % t.type
    print 't.function: %r' % t.function
    #print help(t.function)

    print 't.type.type: %r' % t.type.type

    loc = t.location

    print(loc)
    print(dir(loc))
    print(type(loc))
    print(repr(loc))
    #print(help(loc))
    print 'loc.file: %r' % loc.file
    print 'loc.line: %r' % loc.line

    # raise RuntimeError('what happens if we get an error here?')


gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION,
                      my_pass_execution_callback)
gcc.register_callback(gcc.PLUGIN_PRE_GENERICIZE,
                      my_pre_genericize_callback)

# Try some insane values:
#gcc.register_callback(-1, my_callback)

# Stupid hack idea: a UI for gcc:
#import gtk
#w = gtk.Window(gtk.WINDOW_TOPLEVEL)
#w.show()
#gtk.main()

#from pprint import pprint
#pprint(tree.subclass_for_code)
