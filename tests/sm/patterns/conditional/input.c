extern void foo(void *);
extern void bar(void *);

void test1(void *ptr)
{
  if (ptr) {
    foo(ptr);
  } else {
    bar(ptr);
  }
}
