#/usr/bin/python
import lightbulb, hikari, json, datetime, asyncio
from peewee import Model, BigIntegerField, AutoField, CharField, BlobField, TimestampField, BooleanField
from playhouse.sqlite_ext import SqliteExtDatabase, JSONField
from base64 import b64encode, b64decode
from hikari.presences import Status


with open("config.json", 'r') as f:
    config: dict = json.load(f)


def array_split(list_, n):
    for x in range(0, len(list_), n):
        every_chunk = list_[x: n+x]
        yield every_chunk


bot = lightbulb.BotApp(token=config['discord_token'], prefix=config['prefix'], intents=(hikari.Intents.ALL_GUILDS_UNPRIVILEGED | hikari.Intents.GUILD_MEMBERS))
db = SqliteExtDatabase("service.db")
users = {}

class Basemodel(Model):
    index = AutoField()

    class Meta:
        database = db

class Staff(Basemodel):
    id = BigIntegerField(unique=True)
    name = CharField()
    avatar = CharField()

class Preset(Basemodel):
    ids = JSONField()
    name = CharField()

class Guild(Basemodel):
    autoban = BooleanField(default=False)
    log_channel = BigIntegerField()

class Member(Basemodel):
    id = BigIntegerField()
    name = CharField()
    reason = BlobField()
    timestamp = TimestampField()

    class Meta:
        table_name = 'blacklist'


db.create_tables([Staff, Preset, Guild, Member])
def _staff_check(ctx: lightbulb.context.Context):
    if ctx.author.id == config['owner_id']:
        return True
    staff = Staff.get_or_none(Staff.id==ctx.author.id)
    if staff is None:
        raise lightbulb.errors.MissingRequiredPermission()
    else:
        return True

def _owner_check(ctx: lightbulb.context.Context):
    if ctx.author.id == config['owner_id']:
        return True
    else:
        raise lightbulb.errors.MissingRequiredPermission()

owner_check = lightbulb.Check(_owner_check)
staff_check = lightbulb.Check(_staff_check)

@bot.command()
@lightbulb.add_checks(owner_check)
@lightbulb.option("user", "The user you want to add to staff", type=lightbulb.converters.UserConverter, required=True)
@lightbulb.command("add_staff", "Ads a user to staff", aliases=['as'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def add_staff(ctx: lightbulb.PrefixContext):
    user: hikari.User = ctx.options.user
    staff = Staff.get_or_none(Staff.id==user.id)
    if staff is None:
        Staff.create(id=user.id, name=f'{user.username}#{user.discriminator}', avatar=user.avatar_url)
        embe = hikari.Embed(title=f"Succesfully added {user.mention} to staff", color=0x3eef6a)
        await ctx.respond(embed=embe)
    else:
        embe = hikari.Embed(title=f"{user.mention} is already in staff", color=0xe53751)
        await ctx.respond(embed=embe)


@bot.command()
@lightbulb.add_checks(owner_check)
@lightbulb.option("user", "The user you want to remove from staff", type=lightbulb.converters.UserConverter, required=True)
@lightbulb.command("remove_staff", "Remove user from staff", aliases=['rs'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def remove_staff(ctx: lightbulb.PrefixContext):
    user: hikari.User = ctx.options.user
    staff = Staff.get_or_none(Staff.id==user.id)
    if staff is not None:
        Staff.delete_instance()
        embe = hikari.Embed(title=f"Succesfully removed {user.mention} from staff", color=0x3eef6a)
        await ctx.respond(embed=embe)
    else:
        embe = hikari.Embed(title=f"{user.mention} isn't in staff ", color=0xe53751)
        await ctx.respond(embed=embe)


@bot.command()
@lightbulb.add_checks(owner_check)
@lightbulb.command("list_staff", "Lists staff", aliases=['ls'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def list_staff(ctx: lightbulb.PrefixContext):
    staff = Staff.select().execute()
    embeds = []
    for i in array_split(staff, 25):
        embe = hikari.Embed(title="Staff:",color=0x4EFFFC)
        for j in i: 
            embe.add_field(name=f"{j.name}", value=f"{j.id}")
        embeds.append(embe)
    if embeds==[]:
        embe = hikari.Embed(title="No data found :(",color=0x4EFFFC)
        await ctx.respond(embed=embe)
        return    
    for i in array_split(embeds, 10):
        await ctx.respond(embeds=i)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.command("list_blacklisted", "Lists blacklisted users", aliases=['lb'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def list_blacklisted(ctx: lightbulb.PrefixContext):
    staff = Member.select().execute()
    embeds = []
    for i in array_split(staff, 25):
        embe = hikari.Embed(title="Blacklisted users:",color=0x4EFFFC)
        for j in i: 
            embe.add_field(name=f"{j.index} -- {j.name}:{j.id}", 
            value=f'Blacklisted at {j.timestamp.isoformat()} for:\n{b64decode(j.reason).decode("utf-8")}')
        embeds.append(embe)
    if embeds==[]:
        embe = hikari.Embed(title="No data found :(",color=0x4EFFFC)
        await ctx.respond(embed=embe)
        return
    for i in array_split(embeds, 10):
        await ctx.respond(embeds=i)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.option("reason", "The reason for blacklisting the user", required=True)
@lightbulb.option("user", "The user you want to blacklist", type=lightbulb.converters.UserConverter, required=True)
@lightbulb.command("blacklist", "Remove user from staff", aliases=['bs','ab','add_blacklist','b', 'add'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def add_blacklist(ctx: lightbulb.PrefixContext):
    user: hikari.User = ctx.options.user
    mem = Member.get_or_none(Staff.id==user.id)
    if mem is None:
        Member.create(id=user.id, name=f'{user.username}#{user.discriminator}', 
        reason=b64encode(ctx.options.reason.encode("utf-8")))
        embe = hikari.Embed(title=f"Succesfully added {user.mention} to the blacklist", 
        description=f"Reason:{ctx.options.reason}", color=0x3eef6a)
        await ctx.respond(embed=embe)
    else:
        embe = hikari.Embed(title=f"{user.mention} is already blacklisted",
        description=f'Blacklisted at {mem.timestamp.isoformat()} for:\n{b64decode(mem.reason).decode("utf-8")}', 
        color=0xe53751)
        await ctx.respond(embed=embe)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.option("user", 'The user you want to remove from the blacklist', type=lightbulb.converters.UserConverter, required=True)
@lightbulb.command("remove", "Remove user from blacklist", aliases=['rb','r',"remove_from_blacklist"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def remove_from_blacklist(ctx: lightbulb.PrefixContext):
    user: hikari.User = ctx.options.user
    mem = Member.get_or_none(Staff.id==user.id)
    if mem is not None:
        Member.delete_instance()
        embe = hikari.Embed(title=f"Succesfully removed {user.mention} from the blacklist", color=0x3eef6a)
        await ctx.respond(embed=embe)
    else:
        embe = hikari.Embed(title=f"{user.mention} isn't blacklisted", color=0xe53751)
        await ctx.respond(embed=embe)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.option("id", "The id of the preset you want to use", required=True)
@lightbulb.command("search_preset", "Search for a preset", aliases=['sp'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def search_preset(ctx: lightbulb.PrefixContext):
    try:
        id = int(ctx.options.id)
    except ValueError:
        embe = hikari.Embed(title=f"Invalid argument passed!\nRun `!help search_preset` to learn how to use this command", color=0xe53751)
        await ctx.respond(embed=embe)
        return
    preset = Preset.get_or_none(Preset.id==id)
    await search(ctx, preset.ids)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.option("id", "The id of the user you want to search for", required=True)
@lightbulb.command("search_user", "Search for a user", aliases=['su'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def search_user(ctx: lightbulb.PrefixContext):
    try:
        id = int(ctx.options.id)
    except ValueError:
        embe = hikari.Embed(title=f"Invalid argument passed!\nRun `!help search_user` to learn how to use this command", color=0xe53751)
        await ctx.respond(embed=embe)
        return
    await search(ctx, [id])


async def search(ctx, ids):
    res = await _search(ids)
    embeds = []
    for i in array_split(res, 25):
        embe = hikari.Embed(title="Results:",color=0x4EFFFC)
        for j in i:
            embe.add_field(name=j['name'], value=j['value'])
        embeds.append(embe)
    if embeds==[]:
        embe = hikari.Embed(title="No data found :(",color=0x4EFFFC)
        await ctx.respond(embed=embe)
        return
    for i in array_split(embeds, 10):
        await ctx.respond(embeds=i)

async def _search(ids):
    global users
    if not isinstance(ids, list):
        ids = [ids]
    res = []
    for id in ids:
        if id in users:
            guilds = users[id]['guilds']
            res.append({"name":f"Found {id} in {len(guilds)} guild(s):", "value":','.join(guilds)})
    return res

@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.option("id", "The id of the preset you want to add users to", required=True)
@lightbulb.command("preset_add", "Add users to a preset", aliases=['pa'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def preset_add(ctx: lightbulb.PrefixContext):
    try:
        id = int(ctx.options.id)
    except ValueError:
        embe = hikari.Embed(title=f"Invalid argument passed!\nRun `!help preset_add` to learn how to use this command", color=0xe53751)
        await ctx.respond(embed=embe)
        return
    preset = Preset.get_or_none(Preset.index==id)
    if preset is not None:
        al = set(preset.ids)
        for user in [int(i) for i in ctx.event.message.content.split(f"{ctx.prefix}{ctx.invoked_with}")[1].split(id, 1)[1].split(" ") if i.isdigit()]:
            al.add(user)
        preset.ids = list(al)
        preset.save()
        embe = hikari.Embed(title=f"Succesfully added {len(al)} user(s) to preset {id}", color=0x4EFFFC)
        await ctx.respond(embed=embe)
    else:
        embe = hikari.Embed(title=f"No preset found with id {id}", color=0xe53751)
        await ctx.respond(embed=embe)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.option("id", "The id of the preset you want to add users to", required=True)
@lightbulb.command("preset_remove", "Add users to a preset", aliases=['pr'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def preset_remove(ctx: lightbulb.PrefixContext):
    try:
        id = int(ctx.options.id)
    except ValueError:
        embe = hikari.Embed(title=f"Invalid argument passed!\nRun `!help preset_remove` to learn how to use this command", color=0xe53751)
        await ctx.respond(embed=embe)
        return
    preset = Preset.get_or_none(Preset.index==id)
    if preset is not None:
        al = 0
        for user in [int(i) for i in ctx.event.message.content.split(f"{ctx.prefix}{ctx.invoked_with}")[1].split(id, 1)[1].split(" ") if i.isdigit()]:
            if user in preset.ids:
                al += 1
                preset.ids.remove(user)
        preset.save()
        embe = hikari.Embed(title=f"Succesfully removed {al} user(s) from preset {id}", color=0x4EFFFC)
        await ctx.respond(embed=embe)
    else:
        embe = hikari.Embed(title=f"No preset found with id {id}", color=0xe53751)
        await ctx.respond(embed=embe)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.option("id", "The id of the preset you want to remove", required=True)
@lightbulb.command("remove_preset", "Remove a preset", aliases=['rp'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def remove_preset(ctx: lightbulb.PrefixContext):
    try:
        id = int(ctx.options.id)
    except ValueError:
        embe = hikari.Embed(title=f"Invalid argument passed!\nRun `!help remove_preset` to learn how to use this command", color=0xe53751)
        await ctx.respond(embed=embe)
        return
    preset = Preset.get_or_none(Preset.index==id)
    if preset is not None:
        preset.delete_instance()
        embe = hikari.Embed(title=f"Succesfully removed preset {id}", color=0x4EFFFC)
        await ctx.respond(embed=embe)
    else:
        embe = hikari.Embed(title=f"No preset found with id {id}", color=0xe53751)
        await ctx.respond(embed=embe)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.command("list_presets", "List all presets", aliases=['lp'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def list_presets(ctx: lightbulb.PrefixContext):
    presets = Preset.select()
    embeds = []
    for i in array_split(presets, 25):
        embe = hikari.Embed(title="Presets:",color=0x4EFFFC)
        for j in i: 
            embe.add_field(name=f"{j.name}", value=f"{j.index}")
        embeds.append(embe)
    for i in array_split(embeds, 10):
        await ctx.respond(embeds=i)


@bot.command()
@lightbulb.add_checks(staff_check)
@lightbulb.option('name', 'The name of the preset you want to create', required=True)
@lightbulb.command("add_preset", "Add a preset", aliases=['ap'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def add_preset(ctx: lightbulb.PrefixContext):
    preset = Preset.create(name=ctx.options.name)
    preset.save()
    embe = hikari.Embed(title=f"Succesfully created preset {preset.id}", color=0x4EFFFC)
    await ctx.respond(embed=embe)


@bot.listen(hikari.MemberCreateEvent)
async def on_member_create(event: hikari.MemberCreateEvent):
    guild = Guild.get_or_none(Guild.id==event.guild_id)
    if guild is not None:
        mem = Member.get_or_none(Member.id==event.member.id)
        if mem is not None:
            await handle_blacklisted(event.member, mem, guild)


async def handle_blacklisted(member: hikari.Member, blacklist_entry: Member, guild: Guild):
    discord_guild = await bot.rest.fetch_guild(member.guild_id)
    global_log_embed = hikari.Embed(title=f"Banned {member.username} in guild {discord_guild.name}", 
        description=f"Banned at {blacklist_entry.timestamp.isoformat()}. Reason:\n{b64decode(blacklist_entry.reason).decode('utf-8')}"
        , color=0x4EFFFC)
    global_log_embed.set_footer(text=datetime.datetime.now().isoformat())
    global_log_embed.set_thumbnail(image=member.avatar_url)
    if guild is not None:
        guild_log_embed = hikari.Embed(title=f"Autobanned {member.username}", description=f"Banned globally at {blacklist_entry.timestamp.isoformat()}. Reason:\n{b64decode(blacklist_entry.reason).decode('utf-8')}"
                , color=0x4EFFFC)
        if guild.autoban is True:
            await member.ban(reason="Blacklisted")
            global_log_embed.title = f"Banned {member.username} in guild {guild.name}"
        else:
            guild_log_embed.title = f"User {member.username} is globally banned"
    else:
        global_log_embed.title = f"{member.username} joined guild {discord_guild.name}"
    await bot.rest.create_message(config['global_log_channel'], embed=global_log_embed)
    if guild is not None:
        await bot.rest.create_message(guild.log_channel, embed=guild_log_embed)


async def sync_members():
    global users
    async for guild in bot.rest.fetch_my_guilds():
        async for member in bot.rest.fetch_members(guild.id):
            if users.get(member.id) is None:
                print(member.display_name)
                users[member.id] = {"id":member.id, "guilds":[guild.id]}
            else:
                if guild.id not in users[member.id]["guilds"]:
                    users[member.id]["guilds"].append(guild.id)


@bot.listen(hikari.ShardReadyEvent)
async def on_shard_ready(event: hikari.ShardReadyEvent):
    await bot.update_presence(status=Status.IDLE)
    await sync_members()
    await bot.update_presence(status=Status.ONLINE)


async def check_users():
    global users
    while True:
        print(users)
        Banned_Members = Member.select().execute()
        for i in Banned_Members:
            if i.id in users:
                user = users[i.id]
                for guild in user['guilds']:
                    mem = await bot.rest.fetch_member(guild, i.id)
                    guild = Guild.get_or_none(Guild.id==guild)
                    await handle_blacklisted(mem, i, guild)
        await asyncio.sleep(900)
        await sync_members()


@bot.command()
@lightbulb.add_checks(lightbulb.has_guild_permissions(hikari.Permissions.ADMINISTRATOR))
@lightbulb.option("autoban", "Whether you want to autoban people or not", type=lightbulb.converters.BooleanConverter,required=True)
@lightbulb.option("log_channel", "The channel you want to log the events in", type=lightbulb.converters.TextableGuildChannelConverter, required=True)
@lightbulb.command("setup", "Setup the bot", aliases=['s'])
@lightbulb.implements(lightbulb.PrefixCommand)
async def setup(ctx: lightbulb.PrefixContext):
    guild = Guild.get_or_none(Guild.id==ctx.message.guild_id)
    if guild is None:
        guild = Guild.create(id=ctx.message.guild_id, autoban=ctx.options.autoban, log_channel=ctx.options.log_channel)
        guild.save()
    else:
        guild.autoban = ctx.options.autoban
        guild.log_channel = ctx.options.log_channel
        guild.save()
    embe = hikari.Embed(title="Succesfully set-up the bot", color=0x4EFFFC)
    await ctx.respond(embed=embe)


@bot.listen(lightbulb.CommandErrorEvent)
async def on_error(event: lightbulb.CommandErrorEvent):
    if isinstance(event.exception, lightbulb.NotEnoughArguments):
        embe = hikari.Embed(title=f"Not enough arguments!\nRun `!help {event.context.command.name}` to learn how to use this command", color=0xe53751)
    elif isinstance(event.exception, lightbulb.CommandNotFound):
        embe = hikari.Embed(title=f'Command not found!\nRun `!help` to see all available commands', color=0xe53751)
    elif isinstance(event.exception, lightbulb.CommandIsOnCooldown):
        embe = hikari.Embed(title=f"You're on cooldown!\n{event.context.command.cooldown} seconds", color=0xe53751)
    elif isinstance(event.exception, lightbulb.errors.MissingRequiredPermission):
        embe = hikari.Embed(title=f"You don't have the required permissions to use this command!", color=0xe53751)
    elif isinstance(event.exception, lightbulb.errors.ConverterFailure):
        embe = hikari.Embed(title=f"Invalid argument passed!\nRun `!help {event.context.command.name}` to learn how to use this command", color=0xe53751)
    else:
        embe = hikari.Embed(title=f"An unknown error occured!", color=0xe53751)
    await event.context.respond(embed=embe)



bot.run()