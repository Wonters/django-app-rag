import mlflow
import functools
import inspect

def mlflow_track(name=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Configure MLflow tracking URI if not properly set
            current_uri = mlflow.get_tracking_uri()
            if not current_uri or current_uri.startswith('file://'):
                # Set to local file system if no tracking server is configured
                mlflow.set_tracking_uri("file:///tmp/mlruns")
            
            run_name = name or func.__name__
            
            # Check if there's already an active run
            active_run = mlflow.active_run()
            use_nested = active_run is not None
            
            # Start run (nested if needed)
            with mlflow.start_run(run_name=run_name, nested=use_nested):
                # Log function arguments
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                mlflow.log_params(bound.arguments)
                result = func(*args, **kwargs)
                # Log result if it's a string or dict
                if isinstance(result, dict):
                    mlflow.log_dict(result, "result.json")
                elif isinstance(result, str):
                    mlflow.log_text(result, "result.txt")
                return result
        return wrapper
    return decorator 