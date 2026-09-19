import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6, description="Password min length 6 chars")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v.strip()):
            raise ValueError("Invalid email format.")
        return v.strip().lower()


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ExtractedFieldsData(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None


class AadhaarExtractionResponse(BaseModel):
    success: bool = True
    message: str = "Aadhaar details extracted successfully."
    extracted_fields: ExtractedFieldsData = Field(default_factory=ExtractedFieldsData)
    missing_fields: list[str] = Field(default_factory=list)
    source: str = "local_mock"

    # Compatibility computed fields so both flat .name and .extracted_fields.name serialize into response
    @computed_field
    @property
    def name(self) -> Optional[str]:
        return self.extracted_fields.name

    @computed_field
    @property
    def date_of_birth(self) -> Optional[str]:
        return self.extracted_fields.date_of_birth

    @computed_field
    @property
    def gender(self) -> Optional[str]:
        return self.extracted_fields.gender

    @computed_field
    @property
    def address(self) -> Optional[str]:
        return self.extracted_fields.address

    model_config = ConfigDict(from_attributes=True)


# Keep ProfileResponse alias for backwards compatibility
ProfileResponse = AadhaarExtractionResponse


class ProfileConfirmRequest(BaseModel):
    name: str = Field(..., min_length=1)
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None


class UserProfileDetailsResponse(BaseModel):
    id: int
    user_id: int
    name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserWithProfileResponse(BaseModel):
    id: int
    email: str
    created_at: Optional[datetime] = None
    profile: Optional[UserProfileDetailsResponse] = None

    model_config = ConfigDict(from_attributes=True)
