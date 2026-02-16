import os
import discord
import aiohttp
import asyncio
from discord import Embed

# -----------------------------
# CONFIG
# -----------------------------
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]
DISCORD_CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
TWITCH_USERNAME = "ItzHoppie"

# -----------------------------
# DISCORD SETUP
# -----------------------------
intents = discord.Intents.default()
client = discord.Client(intents=intents)
is_live = False
access_token = None

# -----------------------------
# TWITCH API FUNCTIONS
# -----------------------------
async def get_twitch_token():
    """Get OAuth token from Twitch for Client Credentials flow"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": TWITCH_CLIENT_ID,
                "client_secret": TWITCH_CLIENT_SECRET,
                "grant_type": "client_credentials"
            }
        ) as resp:
            data = await resp.json()
            return data["access_token"]

async def check_stream():
    """Check if Twitch channel is live and send Discord embed if it just went live"""
    global is_live, access_token

    if not access_token:
        access_token = await get_twitch_token()

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.twitch.tv/helix/streams",
            headers=headers,
            params={"user_login": TWITCH_USERNAME}
        ) as resp:
            data = await resp.json()

            if "data" in data and len(data["data"]) > 0:
                stream = data["data"][0]

                if not is_live:
                    is_live = True
                    channel = client.get_channel(DISCORD_CHANNEL_ID)

                    # Build Twitch embed
                    title = stream["title"]
                    game = stream["game_name"]
                    thumbnail = stream["thumbnail_url"].format(width=1280, height=720)

                    embed = Embed(
                        title=f"{TWITCH_USERNAME} is LIVE!",
                        url=f"https://twitch.tv/{TWITCH_USERNAME}",
                        description=title,
                        color=0x9146FF
                    )
                    embed.add_field(name="Playing", value=game, inline=True)
                    embed.add_field(name="Watch Now", value=f"[Click Here](https://twitch.tv/{TWITCH_USERNAME})", inline=False)
                    embed.set_image(url=thumbnail)

                    await channel.send(content="@everyone", embed=embed)

            else:
                is_live = False

# -----------------------------
# DISCORD EVENTS
# -----------------------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    # Check Twitch every 60 seconds
    while True:
        try:
            await check_stream()
        except Exception as e:
            print(f"Error checking Twitch: {e}")
        await asyncio.sleep(60)

# -----------------------------
# HTTP SERVER TO KEEP RENDER AWAKE
# -----------------------------
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get("/", handle)])

runner = web.AppRunner(app)
asyncio.get_event_loop().run_until_complete(runner.setup())
site = web.TCPSite(runner, "0.0.0.0", 8000)
asyncio.get_event_loop().run_until_complete(site.start())

# -----------------------------
# RUN BOT
# -----------------------------
client.run(DISCORD_TOKEN)
