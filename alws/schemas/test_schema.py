import typing

from pydantic import BaseModel


__all__ = ['TestTaskResult']


class TestTaskResult(BaseModel):
    api_version: str
    result: dict


class TestTask(BaseModel):
    id: int
    package_name: str
    package_version: str
    package_release: typing.Optional[str]
    status: int
    revision: int
    alts_response: dict

    class Config:
        orm_mode = True
