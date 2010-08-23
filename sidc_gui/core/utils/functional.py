def curry(f):
    return lambda *args: f(args)

def uncurry(f):
    return lambda x: f(*x)

def paply(_fn, *args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return _fn(*(args+moreargs), **dict(kwargs, **morekwargs))
    return _curried

