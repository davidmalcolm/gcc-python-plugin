from collections import namedtuple

class TreeType(namedtuple('TreeType', 'SYM, STRING, TYPE, NARGS')):
    def camel_cased_string(self):
        return ''.join([word.title()
                        for word in self.STRING.split('_')])

    # "type" seems to be an "enum_tree_code_class"; see GCC's tree.h

def iter_tree_types():
    import re
    f = open('tree-types.txt')
    for line in f:
        # e.g.
        #   ERROR_MARK, "error_mark", tcc_exceptional, 0
        m = re.match('(.+), (.+), (.+), (.+)', line)
        if m:
            yield TreeType(SYM=m.group(1),
                           STRING=m.group(2)[1:-1],
                           TYPE=m.group(3),
                           NARGS=int(m.group(4)))
        else:
            #    print 'UNMATCHED: ', line
            assert(line.startswith('#') or line.strip() == '')
    f.close()
