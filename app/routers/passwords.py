"""Gerador de senhas."""
from fastapi import APIRouter
from pydantic import BaseModel

from ..services import passwordgen

router = APIRouter(tags=["passwords"])


class PolicyIn(BaseModel):
    length: int = 16
    upper: bool = True
    lower: bool = True
    digits: bool = True
    symbols: bool = True
    exclude_ambiguous: bool = True
    count: int = 1


@router.post("/passwords/generate")
def generate(body: PolicyIn):
    count = min(max(body.count, 1), 20)
    policy = body.model_dump(exclude={"count"})
    return {"passwords": [passwordgen.generate(**policy) for _ in range(count)]}
