def check_allowed(user_id: int, allowed_ids: set[int]) -> bool:
    """Check if user_id is in the allowed set."""
    return user_id in allowed_ids
