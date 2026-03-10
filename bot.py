import os
import discord
from discord.ext import commands, tasks
from discord.ui import View, Select, Button
import asyncio
import re
import time
import datetime
import pytz
import io

# -------------------------------
# BOT SETUP
# -------------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------------
# GLOBAL DATA
# -------------------------------
reklam_data = {}
reklam_messages = {}
user_cooldowns = {}
afk_users = {}

IRAQ_TZ = pytz.timezone("Asia/Baghdad")

# -------------------------------
# UTILITY FUNCTIONS
# -------------------------------
def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    elif minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

# -------------------------------
# PERSISTENT VIEWS (Ticket System)
# -------------------------------
STAFF_ROLE_ID = 1473811528347029546
ADMIN_ROLE_ID = 1473811528347029546
TICKET_CATEGORY_ID = 1471155863874961624
LOG_CHANNEL_ID = 1470512869824135380
TICKET_BANNER = "https://cdn.discordapp.com/attachments/1470512716136583331/1476893117067034749/7892F619-4166-49D0-A34B-8B8D5CED1120.png"

class TicketControl(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Re-Open", style=discord.ButtonStyle.green, custom_id="ticket_reopen")
    async def reopen(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.set_permissions(
            interaction.user,
            overwrite=discord.PermissionOverwrite(read_messages=True, send_messages=True)
        )
        await interaction.response.send_message("🔓 Ticket re-opened!", ephemeral=True)

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.red, custom_id="ticket_delete")
    async def delete(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🗑️ Deleting in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()


class TicketClose(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        guild = interaction.guild
        log_channel = guild.get_channel(LOG_CHANNEL_ID)

        history = [m async for m in interaction.channel.history(limit=None, oldest_first=True)]
        log_text = f"Ticket Transcript: {interaction.channel.name}\n" + "="*60 + "\n"
        for m in history:
            log_text += f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author}:\n"
            if m.content:
                log_text += f"{m.content}\n"
            for attachment in m.attachments:
                log_text += f"[Attachment] {attachment.url}\n"
            log_text += "\n"

        file = discord.File(io.BytesIO(log_text.encode("utf-8")), filename=f"{interaction.channel.name}.txt")
        if log_channel:
            log_embed = discord.Embed(
                title="📄 Ticket Transcript",
                description=f"User: {interaction.user.mention}\nChannel: {interaction.channel.name}",
                color=0xe1a4ff
            )
            await log_channel.send(embed=log_embed, file=file)

        await interaction.channel.set_permissions(
            interaction.user,
            overwrite=discord.PermissionOverwrite(read_messages=True, send_messages=False)
        )

        closed_embed = discord.Embed(
            title="⚪ Ticket Closed",
            description="Transcript saved. You can re-open or delete below.",
            color=0xe1a4ff
        )
        await interaction.followup.send(embed=closed_embed, view=TicketControl())


class TicketDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Apply to Staff", emoji="<a:000Lilac_moon:1476779732879015988>"),
            discord.SelectOption(label="Report", emoji="<a:40335reported:1425217416937603113>"),
            discord.SelectOption(label="Buying things", emoji="<a:000Lilac_moon:1474364668569981102>"),
            discord.SelectOption(label="Others", emoji="<a:11sal:1474329533875359827>")
        ]
        super().__init__(placeholder="Select a category...", options=options, custom_id="ticket_dropdown")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            return await interaction.response.send_message("❌ Ticket category not found.", ephemeral=True)

        ticket_name = f"ticket-{interaction.user.id}"
        if discord.utils.get(category.text_channels, name=ticket_name):
            return await interaction.response.send_message("❌ You already have a ticket!", ephemeral=True)

        staff_role = guild.get_role(STAFF_ROLE_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        if staff_role: overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await category.create_text_channel(name=ticket_name, overwrites=overwrites)
        embed = discord.Embed(
            title="🤍 Lilac Moon Support 🤍",
            description=f"Hello {interaction.user.mention}, please describe your issue.\nEnglish: Please describe your issue.",
            color=0xe1a4ff
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await channel.send(content=f"{interaction.user.mention} @everyone", embed=embed, view=TicketClose())
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)


class MainTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# -------------------------------
# TASK LOOPS
# -------------------------------
@tasks.loop(time=datetime.time(hour=23, minute=59, tzinfo=IRAQ_TZ))
async def reset_reklam():
    reklam_data.clear()
    reklam_messages.clear()
    print("✅ Reklam stats reset for new day (Iraq time)")

@tasks.loop(time=datetime.time(hour=23, minute=59, tzinfo=IRAQ_TZ))
async def auto_daily():
    CHANNEL_ID = 1470512762655604991
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🌙 Daily Reminder",
            description="Greetings! Please do your tasks and be active in the server.",
            color=0xe1a4ff
        )
        await channel.send(content="@everyone", embed=embed)

# -------------------------------
# BOT READY
# -------------------------------
@bot.event
async def on_ready():
    bot.add_view(MainTicketView())
    bot.add_view(TicketClose())
    bot.add_view(TicketControl())
    reset_reklam.start()
    auto_daily.start()
    print(f"Logged in as {bot.user}")

# -------------------------------
# AFK COMMAND
# -------------------------------
@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def afk(ctx, *, reason="No reason provided"):
    user = ctx.author
    if user.id in afk_users:
        return await ctx.send(f"{user.mention}, you are already AFK!", delete_after=5)

    afk_users[user.id] = {"reason": reason, "old_name": user.display_name, "time": time.time(), "pings": 0, "pinged_by": set()}
    try:
        if "[AFK]" not in user.display_name:
            new_nick = f"{user.display_name[:25]} [AFK]"
            await user.edit(nick=new_nick)
    except: pass
    await ctx.send(f"{user.mention} is now AFK! Reason: {reason}")

# -------------------------------
# MESSAGE HANDLER
# -------------------------------
@bot.listen("on_message")
async def handle_all_messages(message):
    if message.author.bot or not message.guild:
        return

    now = time.time()
    author_id = message.author.id

    # 1️⃣ AFK REMOVE
    if author_id in afk_users:
        data = afk_users.pop(author_id)
        duration = format_time(now - data["time"])
        try: await message.author.edit(nick=data["old_name"])
        except: pass
        ping_list = ", ".join([f"<@{uid}>" for uid in data["pinged_by"]])
        ping_info = f" | Mentioned by: {ping_list}" if ping_list else ""
        await message.channel.send(f"👋 Welcome back {message.author.mention}! You were gone for {duration}. Total Pings: {data['pings']}{ping_info}")

    # 2️⃣ AFK MENTION NOTIFICATION
    for user in message.mentions:
        if user.id in afk_users and user.id != author_id:
            data = afk_users[user.id]
            data["pings"] += 1
            data["pinged_by"].add(author_id)
            duration = format_time(now - data["time"])
            await message.channel.send(f"☁️ **{user.display_name}** is AFK ({duration})!\n**Reason:** {data['reason']}", delete_after=15)
            break

    # 3️⃣ LINK TRIGGER
    if message.content.lower() == "link":
        try:
            await message.delete()
            await message.author.send("Welcome to Lilac Moon! [Invite Link](https://discord.gg/Desqjqmbck)")
        except: pass

    # 4️⃣ REKLAM TRIGGER
    TARGET_CHANNEL_ID = 1470512817936273498
    ROLE_ID = 1470512634661961960
    COOLDOWN_SECONDS = 120
    TRIGGER_WORDS = ["reklam"]

    if message.channel.id == TARGET_CHANNEL_ID and message.content.strip().lower() in TRIGGER_WORDS:
        last_used = user_cooldowns.get(author_id, 0)
        if now - last_used >= COOLDOWN_SECONDS:
            user_cooldowns[author_id] = now
            embed = discord.Embed(title="Reklam Request", description=f"Requested by {message.author.mention}. Please wait for staff.", color=0xe1a4ff)
            await message.channel.send(content=f"<@&{ROLE_ID}>", embed=embed)

    await bot.process_commands(message)

# -------------------------------
# RUN BOT
# -------------------------------
bot.run("MTQ3MDczMTc1MjAxMTIwMjU3MA.G2-KAF.vy3Z0GTZcv43Gwh_JfsHIiAvfVmyM8WBdDCjg4")