import os
import discord
from discord.ext import commands, tasks
from discord.ui import View, Select, Button
import io
import asyncio
import re
import time
import datetime
import pytz

# -----------------------------
# BOT SETUP
# -----------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# GLOBAL STORAGE
# -----------------------------
reklam_data = {}
reklam_messages = {}
afk_users = {}
user_cooldowns = {}

IRAQ_TZ = pytz.timezone("Asia/Baghdad")

# -----------------------------
# HELPERS
# -----------------------------
def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    elif minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

def create_daily_embed(guild):
    BANNER_URL = "https://cdn.discordapp.com/attachments/1470512716136583331/1475580357779919099/53A13E31-5864-4EA2-8446-D5A8B3719A45.png"
    embed = discord.Embed(
        title="<:000Lilac_moon:1476320816567288049> `Daily Message` <:000Lilac_moon:1476320816567288049>",
        description=(
            "سڵاوتان لێبێت ئازیزان تکایە ئەرکەکانتان بکەن وە چالاک بن لە سێرڤەر هیوایی ڕۆژێکی خۆش ئەخوازم بۆتان\n\n"
            "<a:000Lilac_moon:1476779732879015988> **English Translation:**\n"
            "Greetings dear ones, please do your tasks and be active in the server. I wish you all a pleasant day."
        ),
        color=0xe1a4ff
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Lilac Moon • Daily Reminder")
    embed.timestamp = discord.utils.utcnow()
    return embed

# -----------------------------
# AUTO RESET REKLAM TASK
# -----------------------------
@tasks.loop(time=datetime.time(hour=23, minute=59, tzinfo=IRAQ_TZ))
async def reset_reklam():
    reklam_data.clear()
    reklam_messages.clear()
    print("✅ Reklam stats reset (Iraq time)")

# -----------------------------
# AUTO DAILY TASK
# -----------------------------
@tasks.loop(time=datetime.time(hour=23, minute=59, tzinfo=IRAQ_TZ))
async def auto_daily():
    CHANNEL_ID = 1470512762655604991
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = create_daily_embed(channel.guild)
        await channel.send(content="@everyone", embed=embed)

# -----------------------------
# TICKET SYSTEM
# -----------------------------
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
            if m.content: log_text += f"{m.content}\n"
            for attachment in m.attachments: log_text += f"[Attachment] {attachment.url}\n"
            log_text += "\n"
        file = discord.File(io.BytesIO(log_text.encode("utf-8")), filename=f"{interaction.channel.name}.txt")
        if log_channel:
            embed = discord.Embed(title="📄 Ticket Transcript", description=f"User: {interaction.user.mention}\nChannel: {interaction.channel.name}", color=0xe1a4ff)
            await log_channel.send(embed=embed, file=file)
        await interaction.channel.set_permissions(interaction.user, overwrite=discord.PermissionOverwrite(read_messages=True, send_messages=False))
        closed_embed = discord.Embed(title="⚪ Ticket Closed", description="Transcript saved. You can re-open or delete below.", color=0xe1a4ff)
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
            return await interaction.response.send_message("❌ You already have an open ticket!", ephemeral=True)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        staff_role = guild.get_role(STAFF_ROLE_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        if staff_role: overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await category.create_text_channel(name=ticket_name, overwrites=overwrites)
        embed = discord.Embed(
            title="🤍 Lilac Moon Support 🤍",
            description=f"Hello {interaction.user.mention}, describe your issue in detail.\nStaff will respond ASAP.",
            color=0xe1a4ff
        )
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        await channel.send(content=f"{interaction.user.mention} @everyone", embed=embed, view=TicketClose())
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class MainTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# -----------------------------
# EVENTS
# -----------------------------
@bot.event
async def on_ready():
    reset_reklam.start()
    auto_daily.start()
    bot.add_view(MainTicketView())
    bot.add_view(TicketClose())
    bot.add_view(TicketControl())
    print(f"Logged in as {bot.user}")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1470512756590383295)
    if channel:
        embed = discord.Embed(
            title="Welcome to Lilac Moon!",
            description=f"Hey {member.mention}! You are member #{member.guild.member_count}",
            color=0xe1a4ff
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

# -----------------------------
# REKLAM TRACKER
# -----------------------------
@bot.listen("on_message")
async def reklam_tracker(message):
    if message.author.bot: return
    SRC_ID = 1470512762655604991
    LOG_ID = 1470512788643516468
    if message.channel.id == SRC_ID:
        found_links = re.findall(r"(discord\.gg\/|discord\.com\/invite\/)\S+", message.content)
        if found_links:
            user_id = message.author.id
            reklam_data[user_id] = reklam_data.get(user_id, 0) + len(found_links)
            count = reklam_data[user_id]
            daily_channel = bot.get_channel(LOG_ID)
            if daily_channel:
                embed = discord.Embed(description=f"{message.author.mention}, thank you!", color=0xe1a4ff)
                embed.add_field(name="Total Reklam Count:", value=f"**{count}**", inline=False)
                embed.set_thumbnail(url=message.author.display_avatar.url)
                msg_id = reklam_messages.get(user_id)
                if msg_id:
                    try:
                        old_msg = await daily_channel.fetch_message(msg_id)
                        await old_msg.edit(content=f"{message.author.mention}", embed=embed)
                    except:
                        new_msg = await daily_channel.send(content=f"{message.author.mention}", embed=embed)
                        reklam_messages[user_id] = new_msg.id
                else:
                    new_msg = await daily_channel.send(content=f"{message.author.mention}", embed=embed)
                    reklam_messages[user_id] = new_msg.id

# -----------------------------
# AFK COMMAND
# -----------------------------
@bot.command()
async def afk(ctx, *, reason="No reason provided"):
    user = ctx.author
    if user.id in afk_users: return await ctx.send(f"{user.mention}, you are already AFK!", delete_after=5)
    afk_users[user.id] = {"reason": reason, "old_name": user.display_name, "time": time.time(), "pings": 0, "pinged_by": set()}
    try:
        if "[AFK]" not in user.display_name:
            await user.edit(nick=f"{user.display_name[:25]} [AFK]")
    except: pass
    await ctx.send(f"🌙 {user.mention} is now AFK! Reason: {reason}")

# -----------------------------
# LINK COMMAND
# -----------------------------
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    if message.content.lower() == "link":
        try:
            await message.delete()
            await message.author.send("🌙 **Welcome to Lilac Moon!**\nHere’s your server link: [Join Server](https://discord.gg/YourServerInvite)")
        except discord.Forbidden:
            await message.channel.send(f"{message.author.mention}, I can't DM you! Please open your DMs.", delete_after=8)
    await bot.process_commands(message)

# -----------------------------
# RUN BOT
# -----------------------------
bot.run("MTQ3MDczMTc1MjAxMTIwMjU3MA.G2-KAF.vy3Z0GTZcv43Gwh_JfsHIiAvfVmyM8WBdDCjg4")