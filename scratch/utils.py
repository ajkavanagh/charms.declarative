
def maybe_format_key(key):
    """Format a key string to replace '-' with '_' so that they can be used
    as attributes.

    :param key: maybe a string.
    :returns: string key
    """
    if isinstance(key, str):
        key = key.replace("-", "_")
    return key


