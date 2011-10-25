/*
   Copyright 2011 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011 Red Hat, Inc.

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

/* Test of adding custom attributes */

/* Function declaration with custom attribs: */
int main(int argc, char *argv[])
    __attribute__((custom_attribute_without_args,
                   custom_attribute_with_one_arg(1066),
                   custom_attribute_with_one_or_two_args("secret agent"),
                   custom_attribute_with_one_or_two_args("elephant", "giraffe") ));

/* Global var declaration with custom attribs: */
int test_global  __attribute__((custom_attribute_without_args,
                                custom_attribute_with_one_arg(1492),
                                custom_attribute_with_one_or_two_args("private investigator"),
                                custom_attribute_with_one_or_two_args("cow", "hedgehog") ));

int main(int argc, char *argv[])
{
    /* Local var declaration with custom attribs: */
    int i __attribute__((custom_attribute_without_args,
                         custom_attribute_with_one_arg(1776),
                         custom_attribute_with_one_or_two_args("haberdasher"),
                         custom_attribute_with_one_or_two_args("turtle", "bear") ));
    return 0;
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
