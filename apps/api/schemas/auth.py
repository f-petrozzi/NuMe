from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    has_profile: bool

    model_config = {"from_attributes": True}
