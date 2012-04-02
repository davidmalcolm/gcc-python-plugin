/*
   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
   Copyright 2012 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
*/

#include "proposed-plugin-api/gcc-common.h"

/* Declarations: functions */

/* gcc_function */
GCC_PUBLIC_API(void)
gcc_function_mark_in_use(gcc_function func);

GCC_PUBLIC_API(gcc_cfg)
gcc_function_get_cfg(gcc_function func);

GCC_PUBLIC_API(int)
gcc_function_get_index(gcc_function func);

GCC_PUBLIC_API(gcc_location)
gcc_function_get_start(gcc_function func);

GCC_PUBLIC_API(gcc_location)
gcc_function_get_end(gcc_function func);

GCC_PUBLIC_API(gcc_function)
gcc_get_current_function(void);

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
