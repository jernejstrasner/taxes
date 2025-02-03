import os
import functools
from datetime import datetime

def cache_daily(cache_file):
    """
    Decorator that caches the result of a function for 24 hours.
    The cache_file parameter specifies where to store the last execution timestamp.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_path = os.path.join('cache', cache_file)
            os.makedirs('cache', exist_ok=True)

            should_execute = True
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    last_run = f.read().strip()
                    today = datetime.now().strftime('%Y-%m-%d')
                    should_execute = last_run != today

            if should_execute:
                print(f"Running {func.__name__}...")
                result = func(*args, **kwargs)
                with open(cache_path, 'w') as f:
                    f.write(datetime.now().strftime('%Y-%m-%d'))
                print(f"Completed {func.__name__}")
                return result
            else:
                print(f"Using cached data for {func.__name__}")
                return None

        return wrapper
    return decorator