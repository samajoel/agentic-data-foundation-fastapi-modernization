def __getattr__(name):
    if name in ('app', 'build_app'):
        from app.main import app, build_app  # noqa: F401
        globals()['app'] = app
        globals()['build_app'] = build_app
        return globals()[name]
    raise AttributeError(f"module 'app' has no attribute {name!r}")
