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

/* GccFunctionI */
GCC_PUBLIC_API(void)
GccFunctionI_MarkInUse(GccFunctionI func);

GCC_PUBLIC_API(GccCfgI)
GccFunctionI_GetCfg(GccFunctionI func);

GCC_PUBLIC_API(int)
GccFunctionI_GetIndex(GccFunctionI func);

GCC_PUBLIC_API(GccLocationI)
GccFunctionI_GetStart(GccFunctionI func);

GCC_PUBLIC_API(GccLocationI)
GccFunctionI_GetEnd(GccFunctionI func);

GCC_PUBLIC_API(GccFunctionI)
Gcc_GetCurrentFunction(void);

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
