extern void test2(void *param0, int param1, char param2);

void test1(void *ptr, int i)
{
  test2(ptr, 0, 'A');
}
