from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class RegisterUser(BaseModel):
    email: str
    password: str
    org_name: str
    org_subdomain: str
