class CharacterNotAllowedError(Exception):
    """raised when a character is found in user input that is not allowed to be there"""


class ExternalURLNotAllowedError(Exception):
    """raised when trying to redirect to an external url - bad security >:("""


def validate_integer(i: str, min_value: int = None, max_value: int = None) -> int:
    """
    :param i: the number (as a string) to validate
    :param min_value: the smallest acceptable value of i, can be None (no limit)
    :param max_value: the largest acceptable value of i, can be None (no limit)
    :returns: int(i) if i is an integer between given parameters (inclusive),
        otherwise raises a ValueError
    """
    # TODO: add error descriptions
    try:
        i = int(i)
    except (ValueError, TypeError) as e:
        raise e
    if min_value is not None:
        if i < min_value:
            raise ValueError
    if max_value is not None:
        if i > max_value:
            raise ValueError
    return i


def validate_username(username: str) -> str:
    allowed_chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ._-'
    print(username)
    for char in username:
        if char not in allowed_chars:
            raise CharacterNotAllowedError(f"Found unauthorised character '{char}' in username '{username}'")
    return username


def validate_next(url: str) -> str | None:
    if not url:
        return None
    if url[0] == '/':
        return url
    raise ExternalURLNotAllowedError(f"External URL '{url}' not allowed", url)
