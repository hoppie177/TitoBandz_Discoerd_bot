import os
import discord
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv(dotenv_path="myconfig.env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
TWITCH_USERNAME = "ItzHoppie"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

is_live = False
access_token = None

async def get_twitch_token():
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

                    title = stream["title"]
                    game = stream["game_name"]
                    thumbnail = stream["thumbnail_url"].format(width=1280, height=720)

                    channel = client.get_channel(DISCORD_CHANNEL_ID)

                    embed = discord.Embed(
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

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    while True:
        await check_stream()
        await asyncio.sleep(60)

client.run(DISCORD_TOKEN)

from aiohttp import web
import asyncio

async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get("/", handle)])

runner = web.AppRunner(app)
asyncio.get_event_loop().run_until_complete(runner.setup())
site = web.TCPSite(runner, "0.0.0.0", 8000)
asyncio.get_event_loop().run_until_complete(site.start())


