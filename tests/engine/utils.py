def failing_test(func, args=None, kwargs=None, checker=lambda x: True, exception=Exception):
    kwargs = dict() if kwargs is None else kwargs
    args = list() if args is None else args
    try:
        checker(func(*args, **kwargs))
        raise Exception(f"{func=}, {args=}, {kwargs=} can not be passed")
    except exception:
        pass
