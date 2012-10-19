#include <stdlib.h>

struct foo {
  char buffer[256];
  int i, j, k;
  float x, y, z;
};

struct foo *test(void)
{
  return (struct foo*)malloc(sizeof(struct foo));
}
