# Crash reproducer from:
#  https://fedorahosted.org/pipermail/gcc-python-plugin/2011-October/000121.html

import gcc

class Whatever:
    def doit(self, optpass, fun, *args, **kwargs):
        print("hi bob")

def main(**kwargs):
    w = Whatever()
    gcc.register_callback(gcc.PLUGIN_PASS_EXECUTION, w.doit)

main()
