import gcc

# A callback that raises an exception:
def my_callback(*args, **kwargs):
    raise RuntimeError("This is a test of raising an exception")

gcc.register_callback(gcc.PLUGIN_FINISH_UNIT,
                      my_callback)
