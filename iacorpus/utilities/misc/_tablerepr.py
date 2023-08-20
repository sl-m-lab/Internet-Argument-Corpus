def tablerepr(obj_self):
    """adds a default __repr__ function to base
    used for printing the object
    Borrowed from: http://stackoverflow.com/questions/7756619/python-repr-and-none
    """
    return "<{}({})>".format(
        obj_self.__class__.__name__,
        ', '.join(
            ["{}={}".format(k, repr(obj_self.__dict__[k]))
             for k in sorted(obj_self.__dict__.keys())
             if k[0] != '_']
        )
    )
