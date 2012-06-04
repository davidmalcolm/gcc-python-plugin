namespace top {
  union top_union{
    int i;
    char c;
    float f;
  };
  namespace sub {
     int subs_int;
     void subs_function(void);
     void *foo;
     namespace sub_sub {
	void foo();
     }
  }
  namespace sub_alias = sub;
  namespace sub_alias_alias = sub_alias;
  namespace foo {
    namespace bar {
    }
  }
};
namespace top_alias_of_alias = top::sub;
