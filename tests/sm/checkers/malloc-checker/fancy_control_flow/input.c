#include <stdlib.h>
#include <string.h>

void test(int i, int j)
{
  int k;
  void *ptr;
  for (k = i; k < j; k++) {
    switch(k) {
    case 0:
      ptr = malloc(1024);
      break;
    case 1:
      break;
    case 2:
      break;
    default:
      break;
    }
  }
  memset(ptr, 0, 4096);
  free(ptr);
}
