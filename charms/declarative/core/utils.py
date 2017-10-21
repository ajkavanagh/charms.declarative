import keyword

T = str.maketrans({'-': '_', '.': '_', '/': "__", '\\': "__"})


def maybe_format_key(name):
    """Format a name into a key.  This is so that they can be used as legal
    Python attributes.

    A '-' or '.' becomes an '_'.
    A '/' or `\` becomes '__'
    Any other characters are illegal and will raise an AttributeError

    :param key: maybe a string, if not, then it is just returned.
    :returns: string key
    :raises: AttributeError for illegal characters.
    """
    if not isinstance(name, str):
        return name
    key = name.translate(T)
    if not key.isidentifier() or keyword.iskeyword(key):
        raise AttributeError("name: {}, to key:{} is not a valid identifier"
                             .format(name, key))
    return key


