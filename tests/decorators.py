"""Test decorators for configuration management"""

import functools
import inspect
from typing import Callable

from src.configuration import ConfigProvider, MockConfigProvider, set_config_provider


def with_test_config(func: Callable) -> Callable:
    """Decorator to automatically set up and tear down test configuration provider.

    This decorator expects the test function to have a 'test_provider' parameter
    and automatically handles the provider setup/teardown pattern.

    Works with both sync and async test functions.

    Usage:
        @with_test_config
        def test_something_sync(self, test_provider):
            # Your test code here - provider is already set up
            result = some_function_that_uses_config()
            assert result == expected

        @pytest.mark.asyncio
        @with_test_config
        async def test_something_async(self, test_provider):
            # Your test code here - provider is already set up
            result = await some_function_that_uses_config()
            assert result == expected
    """

    def _find_provider_args(args, kwargs):
        if "test_provider" in kwargs:
            return kwargs["test_provider"]
        for arg in args:
            if isinstance(arg, MockConfigProvider):
                return arg
        raise ValueError("Arg `test_provider` not found. Make sure your test function has such a parameter.")

    if inspect.iscoroutinefunction(func):
        # Async function
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            test_provider: MockConfigProvider = _find_provider_args(args, kwargs)
            original_provider: ConfigProvider = set_config_provider(test_provider)
            try:
                return await func(*args, **kwargs)
            finally:
                set_config_provider(original_provider)

        return async_wrapper

    # Sync function
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        test_provider: MockConfigProvider = _find_provider_args(args, kwargs)
        original_provider: ConfigProvider = set_config_provider(test_provider)
        try:
            return func(*args, **kwargs)
        finally:
            set_config_provider(original_provider)

    return sync_wrapper


def with_config_context(test_provider_arg_name: str = "test_provider"):
    """Parameterized decorator for configuration context management.

    This version allows you to specify the parameter name if it's different from 'test_provider'.

    Usage:
        @pytest.mark.asyncio
        @with_config_context('my_provider')
        async def test_something(self, my_provider):
            # Provider is automatically set up
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the test provider from the specified argument
            test_provider = kwargs.get(test_provider_arg_name)

            if test_provider is None:
                raise ValueError(f"Argument '{test_provider_arg_name}' not found in function parameters.")

            # Set up the provider
            original_provider = set_config_provider(test_provider)

            try:
                return await func(*args, **kwargs)
            finally:
                set_config_provider(original_provider)

        return wrapper

    return decorator
