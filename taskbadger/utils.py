from importlib import import_module


def import_string(dotted_path):
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(f'Module "{module_path}" does not define a "{class_name}" attribute/class') from err
