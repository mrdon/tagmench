# noinspection PyUnresolvedReferences
import asyncio
import json
import logging
import os
from collections import defaultdict
from typing import Dict
from typing import List
from typing import Optional

import quart.flask_patch
from aiohttp.client import _RequestContextManager
from async_oauthlib import OAuth2Session
from oauthlib.oauth2 import OAuth2Token
from quart import make_response
from quart import Quart
from quart import redirect
from quart import render_template
from quart import request
from quart import session
from quart import url_for
from quart.exceptions import NotFound
from quart.exceptions import Unauthorized
from quart_auth import AuthManager
from quart_auth import AuthUser
from quart_auth import current_user
from quart_auth import login_required
from quart_auth import login_user
from quart_auth import logout_user
from tagmench import db
from tagmench import tags
from tagmench.auth import LoginForm
from tagmench.auth import user_required
from tagmench.logging import init_logging
from tagmench.settings import OAUTH_CLIENT_ID
from tagmench.settings import OAUTH_CLIENT_SECRET
from tagmench.settings import OAUTH_REDIRECT_URL

init_logging()
app = Quart(__name__)
db.init_app(app)
app.secret_key = os.environ.get("SECRET_KEY", "not-so-secret")

AuthManager(app)
app.config["QUART_AUTH_COOKIE_SECURE"] = False
app.config["DB_DSN"] = os.environ.get("DATABASE_URL", "")
app.config["DB_HOST"] = os.environ.get("DB_HOST", "localhost")
app.config["DB_PORT"] = os.environ.get("DB_PORT", 5432)
app.config["DB_DATABASE"] = os.environ.get("DB_DATABASE", "tagmench")
app.config["DB_USER"] = os.environ.get("DB_USER", "postgres")
app.config["DB_PASSWORD"] = os.environ.get("DB_PASSWORD", "postgres")
app.secret_key = os.environ.get("SECRET_KEY", "not-so-secret")

log = logging.getLogger(__name__)


@app.before_serving
async def start_bot():
    from tagmench.irc import Bot

    bot = Bot(
        # set up the bot
        irc_token=os.environ["TMI_TOKEN"],
        client_id=os.environ["CLIENT_ID"],
        nick=os.environ["BOT_NICK"],
        prefix=os.environ["BOT_PREFIX"],
        initial_channels=[os.environ["CHANNEL"]],
    )
    asyncio.create_task(bot.start())


@app.errorhandler(Unauthorized)
async def handle_authorized(e):
    return redirect(url_for("login"))


@app.errorhandler(NotFound)
async def handle_notfound(e):
    return "", 404


@app.errorhandler(Exception)
async def handle_any(e):
    log.exception(f"Unexpected exception: {e}")
    return str(e), 500


async def broadcast_to_clients(username: str, maybe_tags: List[str]):
    log.info(f"Broadcasting to {len(app.clients)} clients")
    user_tags = await tags.get_for_username(username)
    new_tags = [tag for tag in maybe_tags if tag not in user_tags]
    for client in app.clients:
        log.info(f"Putting on client: {id(client)}")
        client.put_nowait(
            dict(author=dict(username=username, tags=user_tags), tags=new_tags)
        )


class ServerSentEvent:
    def __init__(
        self,
        data: str,
        *,
        event: Optional[str] = None,
        id: Optional[int] = None,
        retry: Optional[int] = None,
    ) -> None:
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def encode(self) -> bytes:
        message = f"data: {json.dumps(self.data)}"
        if self.event is not None:
            message = f"{message}\nevent: {self.event}"
        if self.id is not None:
            message = f"{message}\nid: {self.id}"
        if self.retry is not None:
            message = f"{message}\nretry: {self.retry}"
        message = f"{message}\r\n\r\n"
        return message.encode("utf-8")


app.clients = set()


@app.route("/login", methods=["GET"])
async def login():
    return await render_template("login.html", form=LoginForm())


@app.route("/health", methods=["GET"])
async def health():
    return "UP", 200


@app.route("/login", methods=["POST"])
async def login_post():
    form = LoginForm()
    if form["guest"].data:
        log.info("Logging in as a guest")
        login_user(AuthUser("guest"))
        return redirect(url_for("index"))
    else:
        github = OAuth2Session(OAUTH_CLIENT_ID, redirect_uri=OAUTH_REDIRECT_URL)
        authorization_url, state = github.authorization_url(
            "https://id.twitch.tv/oauth2/authorize"
        )

        # State is used to prevent CSRF, keep this for later.
        session["oauth_state"] = state
        return redirect(authorization_url)


@app.route("/logout")
async def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/oauth/redirect")
async def oauth_redirect():
    twitch = OAuth2Session(
        OAUTH_CLIENT_ID, state=session["oauth_state"], redirect_uri=OAUTH_REDIRECT_URL
    )
    token: OAuth2Token = await twitch.fetch_token(
        "https://id.twitch.tv/oauth2/token",
        include_client_id=True,
        client_secret=OAUTH_CLIENT_SECRET,
        authorization_response=request.url.replace("http://", "https://"),
    )
    resp = await twitch.get(
        "https://api.twitch.tv/helix/users",
        headers={
            "client-id": OAUTH_CLIENT_ID,
            "authorization": f"Bearer " f"{token.get('access_token')}",
        },
    )
    if resp.status == 200:
        body = await resp.json()
        user = body["data"][0]
        username = user["login"]
        log.info(f"Logging in as user {username}")
        login_user(AuthUser(username))
        return redirect(url_for("index"))


@app.route("/", methods=["GET"])
@login_required
async def index():
    return await render_template(
        "index.html", user=current_user, is_guest=current_user.auth_id == "guest"
    )


@app.route("/tag", methods=["POST"])
@login_required
@user_required
async def tag():
    data = await request.get_json()
    username = data["username"]
    tag_name = data["tag"]
    log.info("Tag received")
    await tags.add(username, tag_name)
    return "", 204


@app.route("/untag", methods=["POST"])
@login_required
@user_required
async def untag():
    data = await request.get_json()
    username = data["username"]
    tag_name = data["tag"]
    log.info("Tag deleted")
    await tags.remove(username, tag_name)
    return "", 204


@app.route("/sse")
@login_required
async def sse():
    try:
        queue = asyncio.Queue()
        app.clients.add(queue)

        async def send_events():
            while True:
                try:
                    data = await queue.get()
                    log.info(f"Sending data: {data}")
                    event = ServerSentEvent(data)
                    yield event.encode()
                except:
                    log.exception("error sending")

        response = await make_response(
            send_events(),
            {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Transfer-Encoding": "chunked",
            },
        )
        response.timeout = None
        return response
    except:
        log.exception("bad error")
        return "", 500
