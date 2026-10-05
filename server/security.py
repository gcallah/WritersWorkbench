"""
security.py: decides whether a request to our endpoints is allowed.
The design is not done yet, so for now every request is allowed.
"""


def is_allowed(user: str, auth_key: str) -> bool:
    """
    Will check that auth_key is the key issued to user.
    For now, it always returns True.
    """
    return True
