import functools


class Query:
    """Queries python objects for their values.

    Args:
        *args: The series of `queryable` functions

    Typical usage would pass in `queryable` functions in order to enable
    the class to perform actions on the passed in python object. For example,
    if three functions are initially passed in (`filter`, `exclude` and `get`),
    and the object being operated on is `[1, 2, 3, 4]`, usage might look like:

    >>> q = Query(filter, exclude, get)
    >>> q = q([1, 2, 3, 4])
    >>> result = q.filter(value > 1).exclude(4)
    >>> assert list(q) == [2, 3]
    """
    def __init__(self, *args, _parent=None):
        self._result = None
        self._cached_result = []
        self._parent = _parent
        self._actions = {arg.__name__: arg for arg in args}

    @property
    def result(self):
        result = self._result
        if result is None and self._parent:
            result = self._parent.result
        return result

    @result.setter
    def result(self, value):
        self._result = value

    def __getattr__(self, name):
        if name in self._actions:
            return self._actions[name](self)
        raise AttributeError()

    def __call__(self, obj):
        self._result = obj
        self._cached_result = []
        return self

    def __iter__(self):
        if self._cached_result:
            for r in self._cached_result:
                yield r
            return None
        for r in self.result:
            self._cached_result.append(r)
            yield r


class Value:
    """Generate deferred comparison object.

    Used to generate functions which return `True` or `False`
    results depending on how the given comparison value compares
    to the comparison object.

    Example usage:
    >>> value = Value()
    >>> q = Q(filter)([1, 2, 3, 4])
    >>> q.filter(value < 3)

    This would use a compatible filter function to compare each value in
    the given list to the value 3, where 1 and 2 would return `True` and
    3 and 4 would return `False`.
    """
    def __init__(self, _getattr=None):
        self._getattr = _getattr

    def _check_attr(self, comp):
        def check(x):
            return comp(self._getattr(x))
        if self._getattr:
            return check
        return comp

    # TODO: These can probably be created programmatically.
    def __eq__(self, other):
        def comp(x):
            return x == other
        return self._check_attr(comp)

    def __lt__(self, other):
        def comp(x):
            return x < other
        return self._check_attr(comp)

    def __gt__(self, other):
        def comp(x):
            return x > other
        return self._check_attr(comp)

    def __getattr__(self, name):
        def _getattr(obj):
            if self._getattr:
                obj = self._getattr(obj)
            return getattr(obj, name)
        return type(self)(_getattr)


def queryable(func):
    """Mark a function as able to be directly used by a `Query`.

    A convenience decorator for functions that take the arguments:
        result(Iterable): the iterable results on which the function operates
        *args: arbitrary positional args
        **kwargs: arbitrary positional keyword args

    and returns the results of that operation.
    """
    @functools.wraps(func)
    def query_wrapper(self):
        def func_wrapper(*args, **kwargs):
            query = type(self)(*self._actions.values(), _parent=self)
            result = func(self, *args, **kwargs)
            query.result = result
            return query
        return func_wrapper
    return query_wrapper


@queryable
def filter(result, *args, **kwargs):
    """Filter out elements of the `result`.

    Args:
        args: filter functions that return a truthy or falsy value depending
              on if the element should be kept in the result.
        kwargs: filter functions that return a truthy or falsy value depending
                on if the named element should be kept in the result.
    """
    for value in args:
        if callable(value):
            result = (r for r in result if value(r))
        else:
            raise NotImplementedError()

    for key, value in kwargs.items():
        if callable(value):
            result = (r for r in result if value(r))
        else:
            raise NotImplementedError()

    return result


@queryable
def exclude(result, *args, **kwargs):
    """Exclude elements of the `result`.

    Args:
        args: filter functions that return a truthy or falsy value depending
              on if the element should be excluded from the result.
        kwargs: filter functions that return a truthy or falsy value depending
                on if the named element should be excluded from the result.
    """
    for value in args:
        result = (r for r in result if r != value)

    for key, value in kwargs.items():
        if callable(value):
            result = (r for r in result if value(r))
        else:
            raise NotImplementedError()

    return result


# Test Usage
value = Value()
Q = Query(filter, exclude)

woah = [1, 2, 3, 4, 5]
result = Q(woah).filter(value > 2)
result2 = result.filter(value > 3)
result3 = result2.exclude(5)


class Bleh:
    """Example class to test testing arbitrary class attributes
    """
    def __init__(self, value):
        self.prop = value

    def __repr__(self):
        return str(self.prop)

assert list(result) == [3, 4, 5], list(result)
assert list(result) == [3, 4, 5], list(result)
assert list(result2) == [4, 5], list(result2)
assert list(result3) == [4], list(result3)


woah = [Bleh(1), Bleh(2), Bleh(3), Bleh(4), Bleh(5)]
result = Q(woah).filter(value.prop > 2)
result2 = result.filter(value.prop > 3)
assert list(result) == woah[2:], list(result)
assert list(result2) == woah[3:], list(result2)


woah = [Bleh(Bleh(1)), Bleh(Bleh(5))]
result = Q(woah).filter(value.prop.prop > 2)
assert list(result) == woah[1:], list(result)


woah = [Bleh(Bleh(Bleh(2))), Bleh(Bleh(Bleh(6)))]
result = Q(woah).filter(value.prop.prop.prop > 3)
assert list(result) == woah[1:], list(result)


# woah2 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
