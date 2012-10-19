#include <stdlib.h>
#include <string.h>

#include "test.h"

void *f(int a)
{
  if (a) {
    void *p = malloc(4096);
    return p;
  } else {
    return NULL;
  }
}

