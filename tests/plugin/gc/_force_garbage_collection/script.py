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

# Verify that we can forcibly invoke GCC's garbage collector,
# (for selftest purposes)

import gcc

# Count the number of garbage collections:
num_ggc_collections = 0
def on_ggc_start():
    global num_ggc_collections
    num_ggc_collections += 1

gcc.register_callback(gcc.PLUGIN_GGC_START,
                      on_ggc_start)

def on_finish():
    # Now traverse all of the data seen at every previous pass
    print('on_finish')

    if 0:
        print('num_ggc_collections: %i ' % num_ggc_collections)

    # Call gcc._force_garbage_collection(), and verify that on_ggc_start
    # gets called:
    old_collections = num_ggc_collections
    gcc._force_garbage_collection()

    # num_ggc_collections should have increased by 1:
    assert num_ggc_collections > 0
    assert num_ggc_collections == old_collections + 1
    print('num_ggc_collections: new - old: %i '
          % (num_ggc_collections - old_collections))

    if 0:
        print('num_ggc_collections: %i ' % num_ggc_collections)

gcc.register_callback(gcc.PLUGIN_FINISH,
                      on_finish)

