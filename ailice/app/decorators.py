import traceback
from functools import wraps

from ailice.app.log import logger
from ailice.app.exceptions import AWExceptionNotReadyForOperation


def atomic_transition(action):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'methodLock'):
                raise AttributeError("Object has no methodLock attribute")
                
            with self.methodLock:
                if getattr(self, f"may_{action}")():
                    try:
                        ret = func(self, *args, **kwargs)
                        getattr(self, action)()
                    except Exception as e:
                        logger.error(f"Call method '{func.__name__}' FAILED, EXCEPTION: {str(e)}\n\nStack: {''.join(traceback.format_stack())}")
                        raise e
                    return ret
                else:
                    logger.error(f"Method '{func.__name__}' cannot be called in state '{self.state}'")
                    raise AWExceptionNotReadyForOperation(f"Method '{func.__name__}' cannot be called in state '{self.state}'. ")
        return wrapper
    return decorator