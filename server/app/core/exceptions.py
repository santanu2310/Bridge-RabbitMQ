from fastapi import status


class AppException(Exception):
    """Base application exception."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class UserAlreadyExistsError(AppException):
    """Exception raised when a user tries to register with an email or username that already exists."""

    def __init__(
        self, detail: str = "User with this email or username already exists."
    ):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InternalServerError(AppException):
    """Exception raised for internal server errors."""

    def __init__(self, detail: str = "An internal server error occurred."):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class EmailNotVerifiedError(AppException):
    """ " Exception raised when a user's email is not verified"""

    def __init__(self, detail: str = "User email is not verified"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
