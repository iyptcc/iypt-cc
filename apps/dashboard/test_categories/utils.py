class Log():
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @classmethod
    def info(cls,s):
        print("\n%s%s%s%s"%(cls.OKBLUE,cls.BOLD,s,cls.ENDC))

    @classmethod
    def step(cls,s):
        print("\n%s%s%s%s"%(cls.OKGREEN,cls.BOLD,s,cls.ENDC))
