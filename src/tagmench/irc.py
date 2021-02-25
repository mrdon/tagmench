import asyncio
import logging
import os

from sqlalchemy.engine.url import URL
from textblob import TextBlob
from twitchio import Message
from twitchio.ext import commands

from tagmench import web, db

log = logging.getLogger(__name__)


class Bot(commands.Bot):

    # Events don't need decorators when subclassed
    async def event_ready(self):
        log.info(f"Ready | {self.nick}")
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            dsn = URL(
                drivername=os.getenv("DB_DRIVER", "asyncpg"),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", 5432),
                username=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_DATABASE", "postgres"),
            )

        await db.set_bind(
            dsn,
            echo=os.getenv("DB_ECHO", False),
            min_size=os.getenv("DB_POOL_MIN_SIZE", 5),
            max_size=os.getenv("DB_POOL_MAX_SIZE", 10),
            ssl=os.getenv("DB_SSL", "prefer"),
            loop=asyncio.get_event_loop(),
            **os.getenv("DB_KWARGS", dict()),
        )

    async def event_message(self, message: Message):
        parsed = TextBlob(message.content)
        maybe_tag = set()
        for phrase in parsed.noun_phrases:
            maybe_tag.add(phrase)
        for part in [
            tagged
            for tagged in parsed.tags
            if tagged[1] in ("NNS", "NN", "NNP", "NNPS")
        ]:
            maybe_tag.add(part[0])

        log.info(f"Tags: {maybe_tag}")

        try:
            await web.broadcast_to_clients(message.author.name, list(maybe_tag))
        except:
            log.exception("Unexpected issue broadcasting")
        await self.handle_commands(message)

    # Commands use a different decorator
    @commands.command(name="test")
    async def my_command(self, ctx):
        await ctx.send(f"Hello {ctx.author.name}!")
