from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    email: str | None
    username: str | None
    role: str
    has_profile: bool

    model_config = {"from_attributes": True}
