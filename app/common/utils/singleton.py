"""Singleton metaclass implementation."""


class Singleton(type):
    """Singleton metaclass ensuring only one instance of a class."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
