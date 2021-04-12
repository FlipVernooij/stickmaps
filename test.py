from pprint import pprint

from Utils.Map import TileWorkerObject


class first:
    def __init__(self):
        super().__init__()
        print('first')

class second:
    def __init__(self):
        super().__init__()
        print('second')

class third:
    def __init__(self):
        super().__init__()
        print('third')

class parent(first, second, third):
    def __init__(self):
        super().__init__()
        print('parent')

obj = parent()
pprint(parent.__mro__)
pprint(TileWorkerObject.__mro__)