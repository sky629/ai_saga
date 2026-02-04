from uuid import UUID

from uuid_utils import uuid7


def get_uuid7() -> UUID:
    """Generate a UUIDv7 and return it as a standard uuid.UUID object.

    This wrapper is necessary because uuid_utils.UUID is not a subclass of uuid.UUID,
    which causes Pydantic validation errors when used directly.
    """
    return UUID(str(uuid7()))
