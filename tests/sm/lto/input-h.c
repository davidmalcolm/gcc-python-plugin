#include <stdlib.h>
#include <string.h>

#include "test.h"

void h(int c)
{
  int *r = (int*)f(c);
  r[0] = 42; /* BUG: the malloc in f could have failed */
  g(c, r);
  free(r); /* BUG: doublefree here, given that g frees the ptr */
}
