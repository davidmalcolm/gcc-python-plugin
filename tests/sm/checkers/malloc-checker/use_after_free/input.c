#include <stdlib.h>
#include <string.h>

void foo(void *ptr);

void test(int i)
{
  void *p;

  p = malloc(1024);
  if (p) {
    free(p);
    foo(p);
  }
}
