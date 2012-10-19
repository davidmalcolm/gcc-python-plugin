#include <stdlib.h>
#include <string.h>

#include "test.h"

void g(int b, void *q)
{
  if (b==2) {
    g(b, q); /* contrived infinite recursion */
  }
  free(q);
}
