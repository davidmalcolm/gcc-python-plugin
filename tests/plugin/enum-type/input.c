/*
   Copyright 2015 Tom Tromey <tom@tromey.com>

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

enum the_enum
{
  ONE = 1,
  TWO = 2,
  MINUS_ONE = -1
};

/* We need a variable because some versions of gcc don't call
   PLUGIN_FINISH_TYPE for an enum.  */
enum the_enum variable;
