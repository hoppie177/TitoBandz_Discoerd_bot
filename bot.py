import os
import discord
import aiohttp
import asyncio
from discord import Embed
from aiohttp import web

# -----------------------------
# CONFIG
# -----------------------------
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]
DISCORD_CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
TWITCH_USERNAME = "ItzHoppie"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

session = None
access_token = None
last_stream_id = None  # prevents duplicate announcements


# -----------------------------
# TWITCH AUTH
# -----------------------------
async def get_twitch_token():
    global access_token
    async with session.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
    ) as resp:
        data = await resp.json()
        access_token = data["access_token"]


# -----------------------------
# CHECK STREAM
# -----------------------------
async def check_stream():
    global access_token, last_stream_id

    if not access_token:
        await get_twitch_token()

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }

    async with session.get(
        "https://api.twitch.tv/helix/streams",
        headers=headers,
        params={"user_login": TWITCH_USERNAME}
    ) as resp:

        # Refresh token if expired
        if resp.status == 401:
            await get_twitch_token()
            return

        data = await resp.json()

        if data.get("data"):
            stream = data["data"][0]
            stream_id = stream["id"]

            # Only announce NEW streams
            if stream_id != last_stream_id:
                last_stream_id = stream_id

                channel = client.get_channel(DISCORD_CHANNEL_ID)
                if channel is None:
                    print("Channel not found.")
                    return

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
                embed.add_field(
                    name="Watch Now",
                    value=f"[Click Here](https://twitch.tv/{TWITCH_USERNAME})",
                    inline=False
                )
                embed.set_image(url=thumbnail)

                try:
                    # ⚠️ Removed @everyone to avoid 429 spam
                    await channel.send(embed=embed)
                    print("Live notification sent.")
                except discord.HTTPException as e:
                    if e.status == 429:
                        print("Rate limited by Discord. Waiting...")
                        await asyncio.sleep(5)
                    else:
                        raise
        else:
            # Stream offline → reset stream ID
            last_stream_id = None


# -----------------------------
# BACKGROUND LOOP
# -----------------------------
async def twitch_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            await check_stream()
        except Exception as e:
            print(f"Error checking Twitch: {e}")
        await asyncio.sleep(60)


# -----------------------------
# HTTP SERVER (Render)
# -----------------------------
async def start_http_server():
    async def handle(request):
        return web.Response(text="Bot is alive!")

    app = web.Application()
    app.add_routes([web.get("/", handle)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    print("HTTP server running on port 8000")


# -----------------------------
# DISCORD EVENTS
# -----------------------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(twitch_loop())


# -----------------------------
# MAIN ENTRYPOINT
# -----------------------------
async def main():
    global session
    session = aiohttp.ClientSession()

    try:
        await asyncio.gather(
            start_http_server(),
            client.start(DISCORD_TOKEN)
        )
    finally:
        await session.close()


asyncio.run(main())
