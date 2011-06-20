import gcc
import gccutils

def on_finish_unit():
    fn_type_decl = gccutils.get_global_typedef('example_fn_type')
    assert isinstance(fn_type_decl, gcc.TypeDecl)

    print('fn_type_decl.name: %r' % fn_type_decl.name)

    fn_type = fn_type_decl.type
    assert isinstance(fn_type, gcc.FunctionType)
    print('str(fn_type): %r' % str(fn_type))
    print('str(fn_type.type): %r' % str(fn_type.type))
    assert isinstance(fn_type.argument_types, tuple)
    print('argument_types: %r' % [str(t) for t in fn_type.argument_types])



gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      on_finish_unit)
