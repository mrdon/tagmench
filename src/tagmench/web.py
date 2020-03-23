# noinspection PyUnresolvedReferences
import quart.flask_patch
import asyncio
import logging
import os
from collections import defaultdict
from typing import Optional, List, Dict
import json

from quart import Quart, request, make_response, render_template, url_for, redirect
from quart.exceptions import Unauthorized
from quart_auth import AuthManager, login_required, logout_user, login_user, AuthUser, current_user

from tagmench import tags, db
from tagmench.auth import user_required, LoginForm
from tagmench.logging import init_logging

init_logging()
app = Quart(__name__)
db.init_app(app)
app.secret_key = os.environ.get("SECRET_KEY", "not-so-secret")

AuthManager(app)
app.config["QUART_AUTH_COOKIE_SECURE"] = False
app.config["DB_DNS"] = os.environ.get("DATABASE_URL", "")
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
            irc_token=os.environ['TMI_TOKEN'],
            client_id=os.environ['CLIENT_ID'],
            nick=os.environ['BOT_NICK'],
            prefix=os.environ['BOT_PREFIX'],
            initial_channels=[os.environ['CHANNEL']]
        )
    asyncio.create_task(bot.start())


@app.errorhandler(Unauthorized)
async def handle_authorized(e):
    return redirect(url_for('login'))


@app.errorhandler(Unauthorized)
async def handle_any(e):
    log.exception(f"Unexpected exception: {e}")
    return str(e), 500


async def broadcast_to_clients(username: str, maybe_tags: List[str]):
    log.info(f"Broadcasting to {len(app.clients)} clients")
    user_tags = await tags.get_for_username(username)
    new_tags = [tag for tag in maybe_tags if tag not in user_tags]
    for client in app.clients:
        log.info(f"Putting on client: {id(client)}")
        client.put_nowait(dict(author=dict(
            username=username,
            tags=user_tags),
            tags=new_tags))


class ServerSentEvent:

    def __init__(
            self,
            data: str,
            *,
            event: Optional[str]=None,
            id: Optional[int]=None,
            retry: Optional[int]=None,
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
        return message.encode('utf-8')


app.clients = set()


@app.route('/login', methods=['GET'])
async def login():
    return await render_template('login.html', form=LoginForm())


@app.route('/health', methods=['GET'])
async def health():
    return "OK", 200


@app.route("/login", methods=['POST'])
async def login_post():
    form = LoginForm()
    if form["guest"].data:
        log.info("Logging in as a guest")
        login_user(AuthUser("guest"))
        return redirect(url_for('index'))

    if form.validate_on_submit():
        if form["password"].data == os.getenv("MAIN_PASSWORD", "happytogether"):
            log.info("Logging in as a user")
            login_user(AuthUser("1"))
            return redirect(url_for('index'))

    return redirect(url_for('login'))


@app.route("/logout")
async def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/', methods=['GET'])
@login_required
async def index():
    return await render_template('index.html', user=current_user, is_guest=current_user.auth_id == "guest")


@app.route('/tag', methods=['POST'])
@login_required
@user_required
async def tag():
    data = await request.get_json()
    username = data["username"]
    tag_name = data["tag"]
    log.info("Tag received")
    await tags.add(username, tag_name)
    return "", 204


@app.route('/untag', methods=['POST'])
@login_required
@user_required
async def untag():
    data = await request.get_json()
    username = data["username"]
    tag_name = data["tag"]
    log.info("Tag deleted")
    await tags.remove(username, tag_name)
    return "", 204


@app.route('/sse')
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
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Transfer-Encoding': 'chunked',
            },
        )
        response.timeout = None
        return response
    except:
        log.exception("bad error")
        return "", 500