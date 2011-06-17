import gcc

# Callback without any args:
def my_callback(*args, **kwargs):
    print 'my_callback:'
    print '  args: %r' % (args,)
    print '  kwargs: %r' % (kwargs,)

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback)

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback,
                      (1, 2, 3))

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback,
                      foo='bar',
                      baz='qux')

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback,
                      (1, 2, 3),
                      foo='bar',
                      baz='qux')

# (They seem to get invoked in reverse order)

