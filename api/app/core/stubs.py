from typing import NoReturn

from fastapi import HTTPException, status


def not_implemented(feature: str, owner: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"feature": feature, "owner": owner, "status": "not_implemented"},
    )
