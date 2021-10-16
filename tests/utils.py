def failing_test(func, args=[], kwargs={}, checker=lambda x: True, exception=Exception):
    try:
        checker(func(*args, **kwargs))
        raise Exception(f"{func}, {args}, {kwargs} can not be passed")
    except exception:
        pass
