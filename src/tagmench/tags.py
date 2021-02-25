from typing import List

from sqlalchemy import and_

from tagmench.model import Tag


async def get_for_username(username: str) -> List[str]:
    tags = await Tag.query.where(Tag.username == username).gino.all()
    return [tag.name for tag in tags]


async def add(username: str, tag: str):
    await Tag.create(username=username, name=tag)


async def remove(username: str, tag: str):
    await Tag.delete.where(
        and_(Tag.username == username, Tag.name == tag)
    ).gino.status()
