#include <stdlib.h>
#include <string.h>

void test(void *ptr)
{
  free(ptr);

  /* BUG: double-free: */
  free(ptr);
}
