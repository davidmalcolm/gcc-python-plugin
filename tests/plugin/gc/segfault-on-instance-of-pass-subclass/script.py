import gcc

class UnusedArg(gcc.GimplePass):
    def execute(self, fun):
        pass

ps = UnusedArg(name='UnusedArg')
ps.register_after('lower')

gcc._force_garbage_collection()
