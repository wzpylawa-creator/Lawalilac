import discord
from discord.ext import commands, tasks
from discord.ui import View, Select, Button, UserSelect
import sqlite3
import io
import asyncio
import random
import datetime
import re
import time
import typing
import json
import os
import pytz

intents = discord.Intents.default()
intents.members = True  
intents.message_content = True 
intents.voice_states = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# --- STORAGE ---
reklam_data = {}
reklam_messages = {} 
reklam_cooldowns = {} # Added to track the 2-minute wait

@bot.event
async def on_ready():
    bot.add_view(MainTicketView())
    bot.add_view(TicketClose())
    bot.add_view(TicketControl())
    bot.add_view(TempVoiceView())
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1470512756590383295) 
    embed = discord.Embed(
        title=" Welcome to Lilac Moon!",
        description=(
            f"Hey {member.mention} !\n\n"
            "We are **super happy** to have you here.\n\n"
            " **Read the rules:** <#1470512751444099286>\n\n"
            f" You are member **#{member.guild.member_count}**!"
        ),
        color=0xe1a4ff
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_image(url="https://cdn.discordapp.com/attachments/1470512716136583331/1475580357779919099/53A13E31-5864-4EA2-8446-D5A8B3719A45.png?ex=699e00cc&is=699caf4c&hm=be168ea0af4120c1cee652d14d718ef1d75386608b3887d8048fd055a847068d&") 
    embed.set_footer(text="Lilac Moon • Welcome!")
    await channel.send(embed=embed)


# ===============================
# DATA STORAGE
# ===============================
reklam_data = {}
reklam_messages = {}

# ===============================
# IRAQ TIMEZONE
# ===============================
IRAQ_TZ = datetime.timezone(datetime.timedelta(hours=3))

# ===============================
# AUTO RESET TASK (11:59 PM)
# ===============================
@tasks.loop(time=datetime.time(hour=23, minute=59, tzinfo=IRAQ_TZ))
async def reset_reklam():
    global reklam_data, reklam_messages
    reklam_data.clear()
    reklam_messages.clear()
    print("✅ Reklam stats reset for new day (Iraq time)")

# ===============================
# BOT READY
# ===============================
@bot.event
async def on_ready():
    reset_reklam.start()
    print(f"Logged in as {bot.user}")

# ===============================
# ROLES COMMAND
# ===============================
@bot.command(name="roles")
async def show_reklams(ctx, role: discord.Role = None):

    STAFF_ROLE_ID = 1470512621064163351

    is_admin = ctx.author.guild_permissions.administrator
    has_staff = discord.utils.get(ctx.author.roles, id=STAFF_ROLE_ID) is not None

    if not (is_admin or has_staff):
        return await ctx.send("❌ You don't have permission to use this command.", delete_after=3)

    if role is None:
        return await ctx.send("❓ Please mention a role. Example: `!roles @Staff`")

    reklam_list_embed = discord.Embed(
        title=f"Reklam Stats: {role.name}",
        color=0xffffff
    )

    stats_content = ""

    for member in role.members:
        if member.bot:
            continue

        count = reklam_data.get(member.id, 0)
        stats_content += f"{member.mention} **{count}** {'reklam' if count == 1 else 'reklams'}\n"

    reklam_list_embed.description = stats_content if stats_content else "No members found in this role."
    reklam_list_embed.set_footer(text="Lilac Moon Monitoring")

    await ctx.send(embed=reklam_list_embed)

# ===============================
# REKLAM TRACKER
# ===============================
@bot.listen('on_message')
async def reklam_tracker(message):

    if message.author.bot:
        return

    SRC_ID = 1470512762655604991
    LOG_ID = 1470512788643516468

    if message.channel.id == SRC_ID:

        found_links = re.findall(r"(discord\.gg\/|discord\.com\/invite\/)\S+", message.content)

        if found_links:

            user_id = message.author.id
            reklam_data[user_id] = reklam_data.get(user_id, 0) + len(found_links)
            count = reklam_data[user_id]

            if count >= 3:

                daily_channel = bot.get_channel(LOG_ID)

                if daily_channel:

                    reklam_embed = discord.Embed(
                        description=f"{message.author.mention}, thank you for completing your daily reklam!",
                        color=0xe1a4ff
                    )

                    reklam_embed.add_field(
                        name="Total Reklam Count:",
                        value=f"**{count}**",
                        inline=False
                    )

                    reklam_embed.set_thumbnail(url=message.author.display_avatar.url)

                    reklam_embed.set_image(
                        url="https://cdn.discordapp.com/attachments/1470512716136583331/1475580357779919099/53A13E31-5864-4EA2-8446-D5A8B3719A45.png"
                    )

                    reklam_embed.set_footer(text=" Lilac Moon Daily ")

                    msg_id = reklam_messages.get(user_id)

                    if msg_id:
                        try:
                            old_msg = await daily_channel.fetch_message(msg_id)
                            await old_msg.edit(content=f"{message.author.mention}", embed=reklam_embed)
                        except:
                            new_msg = await daily_channel.send(
                                content=f"{message.author.mention}",
                                embed=reklam_embed
                            )
                            reklam_messages[user_id] = new_msg.id
                    else:
                        new_msg = await daily_channel.send(
                            content=f"{message.author.mention}",
                            embed=reklam_embed
                        )
                        reklam_messages[user_id] = new_msg.id

    await bot.process_commands(message)
    
# --- COMMANDS ---

IRAQ_TZ = pytz.timezone("Asia/Baghdad")

# ===============================
# DAILY EMBED FUNCTION
# ===============================

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


# ===============================
# AUTO DAILY MESSAGE (11:59 PM)
# ===============================
@tasks.loop(time=datetime.time(hour=23, minute=59, tzinfo=IRAQ_TZ))
async def auto_daily():
    CHANNEL_ID = 1470512762655604991
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = create_daily_embed(channel.guild)
        await channel.send(content="@everyone", embed=embed)

# ===============================
# SINGLE !DAILY COMMAND
# ===============================
@bot.command(name="daily")
async def daily(ctx):
    # Permission Check
    MINIMUM_ROLE_ID = 1470512626571149515
    target_role = ctx.guild.get_role(MINIMUM_ROLE_ID)
    
    # Check if user has the role or is Admin
    has_role = any(role >= target_role for role in ctx.author.roles) if target_role else False
    is_admin = ctx.author.guild_permissions.administrator

    if not (has_role or is_admin):
        await ctx.send("❌ **Permission Denied:** Staff only.", delete_after=5)
        return

    BANNER_URL = "https://cdn.discordapp.com/attachments/1470512716136583331/1475580357779919099/53A13E31-5864-4EA2-8446-D5A8B3719A45.png"

    embed = discord.Embed(
        title="<:000Lilac_moon:1476320816567288049>  `Daily Message` <:000Lilac_moon:1476320816567288049> ",
        description=(
            "سڵاوتان لێبێت ئازیزان تکایە ئەرکەکانتان بکەن وە چالاک بن لە سێرڤەر هیوایی ڕۆژێکی خۆش ئەخوازم بۆتان\n\n"
            "<a:000Lilac_moon:1476779732879015988> **English Translation:**\n"
            "Greetings dear ones, please do your tasks and be active in the server. I wish you all a pleasant day.\n\n"
            f"<a:000Lilac_moon:1474330105730961553> **Sent by:** {ctx.author.mention}"
        ),
        color=0xe1a4ff
    )
    
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Lilac Moon • Daily Reminder", icon_url=ctx.author.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()

    await ctx.send(content="@everyone", embed=embed)
    try:
        await ctx.message.delete()
    except:
        pass

# ===============================
# BOT READY (Only one allowed)
# ===============================
@bot.event
async def on_ready():
    if not auto_daily.is_running():
        auto_daily.start()
    print(f"Logged in as {bot.user}")

    
    # --- CONFIGURATION ---
    MIN_REQUIRED_ROLE_ID = 1473811528347029546  # Replace with the ID of the lowest role allowed to use this
    ROLE_ID_1 = 1470512634661961960  
    ROLE_ID_2 = 1470512633022124228  
    CHANNEL_ID = 1470512793647186121  
    BANNER_URL = "https://cdn.discordapp.com/attachments/1470512716136583331/1475580357779919099/53A13E31-5864-4EA2-8446-D5A8B3719A45.png?ex=699e00cc&is=699caf4c&hm=be168ea0af4120c1cee652d14d718ef1d75386608b3887d8048fd055a847068d&"
    
    # 1. Check if the user has the required role or higher
    min_role = ctx.guild.get_role(MIN_REQUIRED_ROLE_ID)
    
    if not min_role:
        return await ctx.send("❌ **Error:** Minimum required role not found. Check the ID.")

    # This checks if the user's highest role is at or above the min_role position
    if ctx.author.top_role.position < min_role.position:
        return await ctx.send("❌ **Access Denied:** You don't have a high enough rank to use this.")

    # --- LOGIC ---
    role1 = ctx.guild.get_role(ROLE_ID_1)
    role2 = ctx.guild.get_role(ROLE_ID_2)
    log_channel = bot.get_channel(CHANNEL_ID)

    if not role1 or not role2:
        return await ctx.send("❌ **Error:** Staff roles not found. Check IDs.")

    try:
        await member.add_roles(role1, role2)
        embed = discord.Embed(
            title="❄️ New Staff Member Joined!",
            description=(f"Welcome to the team {member.mention}!\n\n"
                         f"✨ **Roles Granted:** {role1.mention} & {role2.mention}\n"
                         f"🛡️ **Promoted By:** {ctx.author.mention}"),
            color=0xffffff
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=BANNER_URL)

        if log_channel:
            await log_channel.send(content="@everyone", embed=embed)
            await ctx.send(f"✅ {member.mention} is now staff!")
            
    except discord.Forbidden:
        await ctx.send("❌ **Permission Error:** My role must be higher than the roles I am trying to give.")

@bot.command(name="nckm")
@commands.has_permissions(manage_nicknames=True)
async def nckm(ctx, member: discord.Member, *, new_name: str):
    bold_sans = {
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 
        'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 
        'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅', 
        'y': '𝘆', 'z': '𝘇',
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 
        'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 
        'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 
        'Y': '𝗬', 'Z': '𝗭'
    }
    formatted_name = "".join(bold_sans.get(c, c) for c in new_name)
    try:
        await member.edit(nick=formatted_name)
        await ctx.send(f"✅ Changed {member.mention}'s name to **{formatted_name}**")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname (Role Hierarchy).")

@bot.command(name="resetdone")
async def resetdone(ctx):
    reklam_data.clear()
    reklam_messages.clear()
    await ctx.send("🧹 Reset complete.")

@bot.command(name="ann")
@commands.has_permissions(administrator=True)
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    # Split the input by the "|" character
    parts = [p.strip() for p in message.split("|")]
    
    # Validation: Ensure at least Title and Description are present
    if len(parts) < 2:
        await ctx.send("❌ **Usage:** `!ann #channel Title | Description | Banner URL | HexColor`")
        return

    # Extract parts with defaults for optional fields
    title = parts[0]
    description = parts[1]
    banner_url = parts[2] if len(parts) > 2 else None
    
    # Handle Color: Convert hex string (e.g., #ffffff) to integer
    embed_color = 0x2b2d31  # Default dark theme color
    if len(parts) > 3:
        try:
            color_str = parts[3].replace("#", "")
            embed_color = int(color_str, 16)
        except ValueError:
            pass # Keep default if color is invalid

    # Build the Embed
    embed = discord.Embed(title=title, description=description, color=embed_color)
    
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    
    if banner_url and banner_url.lower() != "none":
        embed.set_image(url=banner_url)
        
    await channel.send(content="@everyone", embed=embed)

# ===============================
# 🌙 LILAC MOON TICKET SYSTEM
# ===============================

STAFF_ROLE_ID = 1473811528347029546
ADMIN_ROLE_ID = 1473811528347029546  # 🔥 PUT REAL ADMIN ROLE ID HERE
TICKET_CATEGORY_ID = 1471155863874961624
LOG_CHANNEL_ID = 1470512869824135380
TICKET_BANNER = "https://cdn.discordapp.com/attachments/1470512716136583331/1476893117067034749/7892F619-4166-49D0-A34B-8B8D5CED1120.png"

# -------------------------------
# 🔓 REOPEN / DELETE VIEW
# -------------------------------

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


# -------------------------------
# 🔒 CLOSE BUTTON VIEW
# -------------------------------

class TicketClose(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: Button):

        await interaction.response.defer()

        guild = interaction.guild
        log_channel = guild.get_channel(LOG_CHANNEL_ID)

        # 🔥 Transcript with attachments
        history = [m async for m in interaction.channel.history(limit=None, oldest_first=True)]
        log_text = f"Ticket Transcript: {interaction.channel.name}\n"
        log_text += "=" * 60 + "\n"

        for m in history:
            log_text += f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author}:\n"
            if m.content:
                log_text += f"{m.content}\n"

            for attachment in m.attachments:
                log_text += f"[Attachment] {attachment.url}\n"

            log_text += "\n"

        file = discord.File(
            io.BytesIO(log_text.encode("utf-8")),
            filename=f"{interaction.channel.name}.txt"
        )

        if log_channel:
            log_embed = discord.Embed(
                title="📄 Ticket Transcript",
                description=f"User: {interaction.user.mention}\nChannel: {interaction.channel.name}",
                color=0xe1a4ff
            )
            await log_channel.send(embed=log_embed, file=file)

        # 🔒 Lock user (read only)
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


# -------------------------------
# 🎟️ DROPDOWN
# -------------------------------

class TicketDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Apply to Staff", emoji="<a:000Lilac_moon:1476779732879015988>"),
            discord.SelectOption(label="Report", emoji="<a:40335reported:1425217416937603113>"),
            discord.SelectOption(label="Buying things", emoji="<a:000Lilac_moon:1474364668569981102>"),
            discord.SelectOption(label="Others", emoji="<a:11sal:1474329533875359827>")
        ]

        super().__init__(
            placeholder="Select a category...",
            options=options,
            custom_id="ticket_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)

        if not category:
            return await interaction.response.send_message(
                "❌ Ticket category not found. Contact admin.",
                ephemeral=True
            )

        # 🔥 Unique ticket name
        ticket_name = f"ticket-{interaction.user.id}"

        if discord.utils.get(category.text_channels, name=ticket_name):
            return await interaction.response.send_message(
                "❌ You already have an open ticket!",
                ephemeral=True
            )

        staff_role = guild.get_role(STAFF_ROLE_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await category.create_text_channel(
            name=ticket_name,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🤍 Lilac Moon Support 🤍",
            description=(
                f"سڵاو {interaction.user.mention} 💜\n"
                "تکایە کێشەکەت بە وردی بنووسە.\n"
                "هەوڵ دەدەین بە زوترین کات وەڵامی بەڕێزت بدەینەوە.\n\n"
                "**English:**\n"
                "Please describe your issue in detail.\n"
                "Our staff will respond as soon as possible."
            ),
            color=0xe1a4ff
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # 🔥 NOW MENTIONS EVERYONE
        await channel.send(
            content=f"{interaction.user.mention} @everyone",
            embed=embed,
            view=TicketClose()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )


# -------------------------------
# 🧩 MAIN VIEW
# -------------------------------

class MainTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


# -------------------------------
# 🎫 PANEL COMMAND
# -------------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="🤍 Lilac Moon Support Center 🤍",
        description=(
            "Welcome to our official support center.\n\n"
            "• Select a category below to open a private ticket.\n"
            "• Please wait patiently for staff response.\n\n"
            "تکایە بەشێک هەڵبژێرە بۆ دروستکردنی تیکتی تایبەت."
        ),
        color=0xe1a4ff
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_image(url=TICKET_BANNER)

    embed.set_footer(
        text="Lilac Moon • Support System 🌙",
        icon_url=guild.icon.url if guild.icon else None
    )

    await ctx.send(embed=embed, view=MainTicketView())


# -------------------------------
# 🔄 PERSISTENT VIEWS
# -------------------------------

@bot.event
async def on_ready():
    bot.add_view(MainTicketView())
    bot.add_view(TicketClose())
    bot.add_view(TicketControl())
    print("🌙 Lilac Moon Ticket System Ready.")
            
# --- AUTO EMBED SECTION ---

PROOFS_CHANNEL_ID = 1470512741625106454
FEEDBACK_CHANNEL_ID = 1470512744439484541

PROOFS_BANNER_URL = "https://cdn.discordapp.com/attachments/1470512741625106454/1471582075206500566/photo-output.jpg?ex=698f751b&is=698e239b&hm=8e45c7face126d58cbf8680adcaa011938fbeeafed0bc80a81741749ff1134d4&"
FEEDBACK_BANNER_URL = "https://cdn.discordapp.com/attachments/1470512744439484541/1471593968453292236/photo-output_1.jpg?ex=698f802e&is=698e2eae&hm=3734a3fd8f10763cd392b32dfbad472ab766ae17548bfe5e28ed674f63f3fc33&"

@bot.listen('on_message')
async def auto_embed_handler(message):
    if message.author.bot:
        return

    # Handle Proofs Channel (DO NOT DELETE ORIGINAL IMAGE)
    if message.channel.id == PROOFS_CHANNEL_ID and message.attachments:
        embed = discord.Embed(
            title="⚪ New Store Proof ⚪",
            description=f"🤍 **Sent by:** {message.author.mention}\n◽ Store | Proof!",
            color=0xffffff
        )
        embed.set_image(url=PROOFS_BANNER_URL)
        embed.set_thumbnail(url=message.attachments[0].url)
        embed.set_footer(text=f"Lilac Moon • {message.author}", icon_url=message.author.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        # await message.delete()  <-- This line is removed so image stays
        await message.channel.send(embed=embed)

    # Handle Feedback Channel (Delete text to replace with embed)
    elif message.channel.id == FEEDBACK_CHANNEL_ID and message.content:
        embed = discord.Embed(
            title="⚪ New Feedback ⚪",
            description=f"🤍 **Sent by:** {message.author.mention}\n\n**Feedback:**\n{message.content}",
            color=0xffffff
        )
        embed.set_image(url=FEEDBACK_BANNER_URL)
        if message.attachments:
            embed.set_thumbnail(url=message.attachments[0].url)
        elif message.guild.icon:
            embed.set_thumbnail(url=message.guild.icon.url)
            
        embed.set_footer(text=f"Frozen Salvatore • {message.author}", icon_url=message.author.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await message.delete() # We still delete feedback text to keep it aesthetic
        await message.channel.send(embed=embed)

# --- Chats welcome ---
@bot.listen('on_member_join')
async def chats_welcome(member):
    # REPLACE THE ID BELOW WITH YOUR CHANNEL ID
    channel = bot.get_channel(1470512817936273498)
    
    if channel:
        # White Aesthetic Embed with "Land" and Original Emojis
        embed = discord.Embed(
            description=f"🕊️ __**Welcome {member.mention} 🤍 to our Land**__ 🕊️",
            color=0xFFFFFF  # Pure White Aesthetic
        )

        # Replace the link below with your actual URL banner
        embed.set_image(url="https://cdn.discordapp.com/attachments/1470512716136583331/1471608929548112137/IMG_1182.jpg?ex=698f8e1d&is=698e3c9d&hm=8eb513a8277229efcad18e9ee8e07a14f42af1f53ecb94637082ac866208c89a&")
        
        # Subtle white-themed footer
        embed.set_footer(text="🦢 A new journey begins in the Land...")

        # Sends a mention outside the embed so they get a notification
        await channel.send(content=f"Welcome to the Land, {member.mention}", embed=embed)

            
# --- NEW STAFF RULES COMMAND ---
@bot.command(name="staffrules")
async def staffrules(ctx):
    # Setup your IDs here
    rule1_channel = "1471930813460381757"  # Replace with correct Channel ID
    rule2_channel = "1471930813460381757"  # Replace with correct Channel ID
    rule8_channel = "1470512751444099286"  # Replace with correct Channel ID
    mention_role  = "1470512629146718359"  # Replace with correct Role ID
    banner_url    = "https://cdn.discordapp.com/attachments/1470512716136583331/1475580357779919099/53A13E31-5864-4EA2-8446-D5A8B3719A45.png?ex=699e00cc&is=699caf4c&hm=be168ea0af4120c1cee652d14d718ef1d75386608b3887d8048fd055a847068d&"

    embed = discord.Embed(
        title="🛡️ Staff Guidelines & Regulations\nڕێنمایی و یاساکانی ستاف",
        description=(
            "🗞️ **Staff members must observe and adhere to these rules:**\n"
            "ستافەکان پێویستە ڕەچاوی ئەم خاڵانە بکەن و پابەند بن پێوەیان\n\n"
            "📝 **Daily Duties | ئەرکە ڕۆژانەکان**\n"
            f"* 📢 **Rule 1:** Staff must do their daily advertisement; if you fail to do so, you must state the reason in the <#{rule1_channel}> section.\n"
            f"  > ١. ڕۆژانە ڕیکلامی خۆت دەکەیت؛ گەر نەتکرد، لە بەشی <#{rule1_channel}> دەنوسیت کە بۆ مەجالت نییە.\n\n"
            f"* 🎙️ **Rule 2:** You must be in the server voice channel for 2 hours daily; if you are not, you must write the reason in the <#{rule2_channel}> section.\n"
            f"  > ٢. دەبێت ڕۆژانە ٢ سەعات لە ڤۆیسی سێرڤەر بیت؛ گەر نەتکرد، دەبێ هۆکار بنوسی لە بەشی <#{rule2_channel}>.\n\n"
            "* 🤝 **Rule 3:** You must welcome members and answer their questions if necessary.\n"
            "  > ٣. بەخێر هاتنی مێمبەرەکان بکەن و لە کاتی هەبوونی پرسیار وەڵامیان بدەنەوە.\n\n"
            "⚖️ **Conduct & Respect | ڕەفتار و ڕێزگرتن**\n"
            "* ✨ **Rule 4:** Show respect as stated in the server rules.\n"
            "  > ٤. ڕێز گرتن وەک لە یاسای سێرڤەر نوسراوە.\n\n"
            "* 🚫 **Rule 5:** Do not ask for roles under any circumstances.\n"
            "  > ٥. داوای ڕۆڵ مەکە بە هیچ جۆرێک.\n\n"
            "* 👤 **Rule 6:** Do not harass the opposite gender in any way; show respect.\n"
            "  > ٦. ڕەگەزی بەرامبەر بە هیچ جۆرێک بێزار مەکە و ڕێز بگرە.\n\n"
            "👑 **Seniority & Procedures | پلەبەرزەکان و ڕێکارەکان**\n"
            f"* 🔥 **Rule 7:** Those who have <@&{mention_role}> must be more active than other staff and perform their duties accurately.\n"
            f"  > ٧. ئەو کەسانەی کە ڕۆڵی <@&{mention_role}> پێوەیە، پێویستە لە ستافەکانی تر ئەکتیڤتر بن و ئیشەکانیان بە وردی بکەن.\n\n"
            f"* 📚 **Rule 8:** Do not ignore the <#{rule8_channel}> section.\n"
            f"  > ٨. بەشی <#{rule8_channel}> فەرامۆش مەکە.\n\n"
            "⚠️ **Important Note:**\n"
            "Please follow these rules to avoid any penalties.\n"
            "تکایە ئەم یاسایانە پەیڕەو بکەن بۆ ئەوەی دوور بن لە هەر سزایەک."
        ),
        color=0xe1a4ff
    )

    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_image(url=banner_url)
    embed.set_footer(text=f"Sent by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

# --- NEW MESSAGE LOGIC (APPENDED) ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.content.lower() == "link":
        try:
            await message.delete()
            await message.author.send("[**Welcome to Frozen Salvatore**](https://cdn.discordapp.com/attachments/1470512716136583331/1470882630911131792/IMG_1143.jpg) [ ْ](https://discord.gg/Desqjqmbck)")
        except: pass
    if message.content.lower() == "reklam":
        role = message.guild.get_role(1470512634661961960)
        embed = discord.Embed(title="⚪ `New Reklam Request` ⚪", description=f"🤍 **Welcome** {message.author.mention}\nWait for staff responses. 🎧", color=0xfffffff)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1470512716136583331/1475580357779919099/53A13E31-5864-4EA2-8446-D5A8B3719A45.png?ex=699e00cc&is=699caf4c&hm=be168ea0af4120c1cee652d14d718ef1d75386608b3887d8048fd055a847068d&")
        await message.channel.send(content=f"{role.mention if role else '@Staff'}", embed=embed)
    await bot.process_commands(message)


import time
import discord
from discord.ext import commands

# Dictionary to store AFK users
afk_users = {}

def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    elif minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

# --- AFK COMMAND ---
@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user) # 1 use per 5 seconds
async def afk(ctx, *, reason="No reason provided"):
    user = ctx.author
    
    # Check if already AFK
    if user.id in afk_users:
        return await ctx.send(f"💤 {user.mention}, you are already AFK!", delete_after=5)

    # Store user data
    afk_users[user.id] = {
        "reason": reason,
        "old_name": user.display_name,
        "time": time.time(),
        "pings": 0,
        "pinged_by": set() # Using a set to keep unique pinger IDs
    }

    # Change Nickname (Try/Except to avoid permission errors)
    try:
        if "[AFK]" not in user.display_name:
            # Discord nicks have a 32 char limit
            new_nick = f"{user.display_name[:25]} [AFK]"
            await user.edit(nick=new_nick)
    except:
        pass

    await ctx.send(f"🌙 {user.mention} is now AFK! Reason: {reason}")

# Error handler for the cooldown
@afk.error
async def afk_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Slow down! Try again in {error.retry_after:.1f}s.", delete_after=3)

# --- AFK EVENTS ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    now = time.time()

    # 1. REMOVE AFK (If the user speaks)
    if message.author.id in afk_users:
        data = afk_users[message.author.id]
        
        # Grace period: Don't remove AFK if it was set less than 10 seconds ago
        # This prevents accidental removal right after typing !afk
        if now - data["time"] > 10: 
            afk_users.pop(message.author.id)
            duration = format_time(now - data["time"])
            
            try:
                await message.author.edit(nick=data["old_name"])
            except:
                pass

            # Format the list of people who pinged them
            ping_list = ", ".join([f"<@{uid}>" for uid in data["pinged_by"]])
            ping_info = f" | Mentioned by: {ping_list}" if ping_list else ""
            
            await message.channel.send(
                f"👋 Welcome back {message.author.mention}! You were gone for {duration}. "
                f"Total Pings: {data['pings']}{ping_info}"
            )
            # Stop processing so we don't trigger the "Mention" logic below
            return await bot.process_commands(message)

    # 2. NOTIFY MENTIONS (If an AFK user is pinged)
    for user in message.mentions:
        # Don't trigger if they ping themselves or if the bot is the one pinged
        if user.id in afk_users and user.id != message.author.id:
            data = afk_users[user.id]
            data["pings"] += 1
            data["pinged_by"].add(message.author.id) # Set handles duplicates automatically
            
            duration = format_time(now - data["time"])
            await message.channel.send(
                f"☁️ **{user.display_name}** is AFK ({duration})!\n"
                f"**Reason:** {data['reason']}",
                delete_after=15 # Keeps the chat clean
            )
            # Break so we don't send multiple messages if they ping the same person twice
            break 

    await bot.process_commands(message)




    # -------- LINK TRIGGER --------
    if message.content.lower() == "link":
        try:
            await message.delete()

            my_private_info = """_ _
∆   𝓛𝓲𝓵𝓪𝓬 𝓜𝓸𝓸𝓷 ✦ .ᐟ [.](https://cdn.discordapp.com/attachments/1470887137602834673/1475641046091436156/1D59F70A-C846-4F2F-BF06-4BACA1ABF693.png?ex=699e3951&is=699ce7d1&hm=2df1c78eaca45e9e730f6d885feda9234cb647065c82754df8e7f6311131963b&) [/Lilac](https://discord.gg/Desqjqmbck) Moon 🌙
-# _ _          ❖ 𝓕𝓻𝓲𝓮𝓷𝓭𝓵𝔂 ﹒ 𝓒𝓱𝓲𝓵𝓵 ﹒ 𝓖𝓪𝓶𝓮 ☕
_ _           ✦ Lilac Moon Server 🌌✨ _ _"""

            await message.author.send(my_private_info)
        except discord.Forbidden:
            print(f"Could not DM {message.author.name}")

    # -------- REKLAM TRIGGER --------
    TARGET_CHANNEL_ID = 1470512817936273498
    ROLE_ID = 1470512634661961960
    COOLDOWN_SECONDS = 120
    TRIGGER_WORDS = ["reklam"]
    EMBED_COLOR = 0xe1a4ff
    EMBED_IMAGE_URL = "https://cdn.discordapp.com/attachments/1408075671795667017/1475620438095695892/53A13E31-5864-4EA2-8446-D5A8B3719A45.png"
    EMBED_THUMBNAIL_URL = "https://cdn.discordapp.com/attachments/1470512716136583331/1475625927471009926/a_03d07bab4e43ac36182f1859aaf37dd7.gif"

    if (
        message.channel.id == TARGET_CHANNEL_ID and
        message.content.strip().lower() in TRIGGER_WORDS
    ):
        current_time = time.time()
        last_used = user_cooldowns.get(message.author.id, 0)

        if current_time - last_used >= COOLDOWN_SECONDS:
            user_cooldowns[message.author.id] = current_time
            role_mention = f"<@&{ROLE_ID}>"

            embed = discord.Embed(
                title="<:000Lilac_moon:1475888606915596442> Reklam Request <:000Lilac_moon:1475888606915596442>",
                description=(
                    f"Requested By: {message.author.mention}\n"
                    f"Please Wait | تکایە چاوەڕوان بە..\n\n"
                    f"🤍 **Please wait until the staffs respond your advertisement.**\n"
                    f"🤍 **تکایە چاوەڕوان بە تاکوو ستافەکان جوابت دەدەنەوە.**"
                ),
                color=EMBED_COLOR
            )

            embed.set_image(url=EMBED_IMAGE_URL)
            embed.set_thumbnail(url=EMBED_THUMBNAIL_URL)

            if message.guild and message.guild.icon:
                embed.set_footer(
                    text=f"{message.guild.name} • Advertisement System",
                    icon_url=message.guild.icon.url
                )
            else:
                embed.set_footer(text="Advertisement System")

            await message.channel.send(content=role_mention, embed=embed)

    # Make sure other commands still work
    await bot.process_commands(message)


bot.run("MTQ3MDczMTc1MjAxMTIwMjU3MA.G2-KAF.vy3Z0GTZcv43Gwh_JfsHIiAvfVmyM8WBdDCjg4")