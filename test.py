# Sample python script, to be run by our gcc plugin (see "make test")
#print "hello world"

import gcc

#import sys
#print 'sys.path:', sys.path
#help(gcc)

print(help(gcc.AddrExpr))
print(gcc.Type)
print(gcc.Type.char)
print(help(gcc.Type))


from gccutils import get_src_for_loc, cfg_to_dot, invoke_dot

def my_pass_execution_callback(*args, **kwargs):
    print('my_pass_execution_callback was called: args=%r  kwargs=%r' % (args, kwargs))
    #help(args[0])
    (optpass, fun) = args
    print 'optpass: %r' % optpass
    print 'dir(optpass): %r' % dir(optpass)
    print 'optpass.name: %r' % optpass.name
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
