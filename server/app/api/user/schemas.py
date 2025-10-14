from pydantic import BaseModel, EmailStr


class EmailVerifyRequest(BaseModel):
    email: EmailStr
    otp: str


class VerifyOtpRequest(BaseModel):
    user_id: str
