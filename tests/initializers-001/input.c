struct foo {
  int first_field;
  char *second_field;
};

struct foo f[] = {
  {42, "giraffe"},
  {37, "elephant"},
  {72, "sea otter"},
};

struct foo g[0];

struct foo h[] = {
  {89, "turtle"},
  {37, "lion"},
};

