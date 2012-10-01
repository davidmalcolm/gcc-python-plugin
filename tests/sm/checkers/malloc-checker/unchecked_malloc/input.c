#include <stdlib.h>
#include <string.h>

void test(void)
{
  void *ptr = malloc(4096);
  memset(ptr, 0, 4096);
}
