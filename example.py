import client
bot = client.Command(prefix = "!")

@bot.command(name = "ping", checks = [lambda m: m.guild], cooldown = client.Cooldown(1, 5, "author"), help = "hi")
async def pong(message, arg, arg2):
    await message.channel.send(f"hai {arg} | {arg2}")

bot.run("token")