from datetime import datetime, timezone


def get_utc_timestamp() -> float:
    """
    :return: UTC timestamp in float
    """
    return get_utc_datetime().timestamp()


def get_utc_datetime() -> datetime:
    """
    :return: UTC timestamp in datetime.datetime
    """
    return datetime.now(tz=timezone.utc)
