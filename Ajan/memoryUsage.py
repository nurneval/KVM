import resource
def using():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return '''usertime=%s systime=%s mem=%s mb '''%(usage[0],usage[1],
                (usage[2]*resource.getpagesize())/1000000.0 )


 #print using("current usage")
