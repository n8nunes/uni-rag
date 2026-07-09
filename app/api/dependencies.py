from fastapi import Header, HTTPException, status

from app.models.schemas import ClassificationEnum, UserSession


async def get_current_user(
    x_user_id: str = Header(default="user_dev_01"),
    x_username: str = Header(default="local_student"),
    x_user_role: str = Header(default="student"),
    x_user_clearance: ClassificationEnum = Header(default=ClassificationEnum.STUDENT_ONLY),
) -> UserSession:
    """
    Local development auth shim.

    In a production identity path this would be replaced with JWT verification.
    Keeping it as a dependency makes the RBAC boundary explicit and testable.
    """
    if x_user_role not in {"student", "faculty", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unknown role supplied by local auth context.",
        )

    return UserSession(
        user_id=x_user_id,
        username=x_username,
        role=x_user_role,
        clearance_level=x_user_clearance,
    )
