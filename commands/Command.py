import discord
import inspect
import asyncio

class Cooldown:
    def __init__(self, rate, per, key):
        self.rate = rate
        self.per = per
        self.key = key
        self.cooldowns = {}

    async def lower_cooldown(self, id):
        await asyncio.sleep(self.per)
        self.cooldowns[id] -=1
        
    def update(self, bot, message: discord.Message):
        id = getattr(message, self.key, message.author).id
        if id in self.cooldowns:
            if self.cooldowns[id] == -1:
                return False
            if self.cooldowns[id] >= self.rate:
                return False
            self.cooldowns[id] += 1
        else:
            self.cooldowns[id] = 1
        bot.loop.create_task(self.lower_cooldown(id))
        return True

class CommandOnCooldown(Exception):
    def __init__(self, retry_after, command):
        self.retry_after = retry_after
        self.command = command

class Client(discord.Client):
    def __init__(self, prefix, **kwargs):
        self.prefix = prefix
        self.commands = {}
        self.aliases = {}
        self.checks = {}
        self.options = {}
        super().__init__()
        self.register_command(self.help)

    async def maybe_coro(self, function, *args, **kwargs):
        if inspect.iscoroutinefunction(function):
            return await function(*args, **kwargs)
        
        return function(*args, **kwargs)
    
    async def help(self, message):
        msg = "\n".join(f"{i}: {self.options[i].get('help', 'No help given')}" for i in self.commands)
        await message.channel.send(f"```{msg}```")

    def register_command(self, coro, **kwargs):
        aliases = kwargs.get("aliases", [])
        if name := kwargs.get("name"):
            self.commands[name] = coro
        else:
            name = coro.__name__
            self.commands[name] = coro
 
        for i in aliases:
            self.aliases[i] = name

        if checks := kwargs.get("checks"):
            self.checks[name] = checks

        if allowed := kwargs.get("only_allowed"):
            self.checks[name] = self.checks.get(name, []).append(lambda m: m.author.id in allowed)

        self.options[name] = kwargs

    def command(self, **kwargs):
        def deco(coro):
            self.register_command(coro, **kwargs)
            return coro
        return deco

    async def on_message(self, message):
        if callable(self.prefix):
            if inspect.iscoroutinefunction(self.prefix):
                prefix = await self.prefix(self, message)
            else:
                prefix = self.prefix(self, message)
        else:
            prefix = self.prefix

        if not message.content.startswith(prefix):
            return

        content = message.content[len(prefix):]
        split = content.split(" ")
        command, arguments = split[0], split[1:]

        if command in self.aliases:
            command = self.aliases[command]

        if command not in self.commands:
            return
        
        if cooldown := self.options[command].get("cooldown"):
            if not cooldown.update(self, message):
                raise CommandOnCooldown(cooldown.per, command)

        if command in self.checks:
            checks = [(self.maybe_coro(check, message)) for check in self.checks[command]]
            if any([not await check for check in checks]):
                return

        coro = self.commands[command]
        signature = inspect.signature(coro)
        if len(signature.parameters) == 1:
            await coro(message)
            return

        arg_count = len(signature.parameters)-1

        args = arguments[:arg_count-1]

        if self.options[command].get("no_consume"):
            args.append(arguments[arg_count])
        else:
            args.append(" ".join(arguments[arg_count-1:]))
            
        for index, para in enumerate(signature.parameters):
            if hasattr(signature.parameters[para].annotation, "convert"):
                args[index] = signature[para].annotation.convert(message, args[index])


        await coro(message, *args)



        


