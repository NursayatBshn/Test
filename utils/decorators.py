import time
import functools

def log_execution(func):
    """Decorator for measuring function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        # In a real project, this could write to LoggerService.
        # print(f"[DEBUG] Function {func.__name__} completed in {end_time - start_time:.4f} sec.")
        return result
    return wrapper
