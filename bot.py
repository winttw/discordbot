import discord
from discord.ext import commands
import json
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = 'bets_data.json'
OWNER_ID = YOUR_USER_ID_HERE  # Replace with your Discord User ID as an int
ALLOWED_CHANNEL_ID = 1257876212710113291  # Channel where set_balance is allowed

def moneyline_to_decimal(ml: int) -> float:
    if ml > 0:
        return round((ml / 100) + 1, 2)
    else:
        return round((100 / abs(ml)) + 1, 2)

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({'users': {}, 'matches': {}, 'next_match_id': 1}, f)
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')

@bot.command()
async def balance(ctx):
    data = load_data()
    user_id = str(ctx.author.id)
    balance = data['users'].get(user_id, 1000)
    await ctx.send(f"{ctx.author.name}, you have ${balance} in virtual currency.")

@bot.command()
async def bet(ctx, match_id: int, amount: int, player: str):
    data = load_data()
    user_id = str(ctx.author.id)
    player = player.lower()

    if str(match_id) not in data['matches']:
        return await ctx.send("Match ID not found.")

    match = data['matches'][str(match_id)]

    if match['resolved']:
        return await ctx.send("This match has already been resolved.")
    if player not in ['a', 'b']:
        return await ctx.send("Choose 'a' or 'b'.")

    balance = data['users'].get(user_id, 1000)
    if amount > balance:
        return await ctx.send("Insufficient funds.")

    data['users'][user_id] = balance - amount
    match['bets'].append({'user': user_id, 'amount': amount, 'side': player})
    save_data(data)

    name = match['playerA'] if player == 'a' else match['playerB']
    await ctx.send(f"{ctx.author.name} bet ${amount} on {name}.")

@commands.has_permissions(administrator=True)
@bot.command()
async def create_match(ctx, playerA: str, playerB: str, moneylineA: int, moneylineB: int):
    data = load_data()
    match_id = data['next_match_id']

    decimalA = moneyline_to_decimal(moneylineA)
    decimalB = moneyline_to_decimal(moneylineB)

    data['matches'][str(match_id)] = {
        'playerA': playerA,
        'playerB': playerB,
        'moneylineA': moneylineA,
        'moneylineB': moneylineB,
        'oddsA': decimalA,
        'oddsB': decimalB,
        'bets': [],
        'resolved': False,
        'winner': None
    }

    data['next_match_id'] += 1
    save_data(data)

    await ctx.send(
        f"📢 Match {match_id}: {playerA} ({moneylineA}) vs {playerB} ({moneylineB})\n"
        f"Use !bet {match_id} amount a/b to bet."
    )

@commands.has_permissions(administrator=True)
@bot.command()
async def result(ctx, match_id: int, winner: str):
    data = load_data()
    winner = winner.lower()

    if str(match_id) not in data['matches']:
        return await ctx.send("Match ID not found.")
    match = data['matches'][str(match_id)]

    if match['resolved']:
        return await ctx.send("Already resolved.")
    if winner not in ['a', 'b']:
        return await ctx.send("Winner must be 'a' or 'b'.")

    match['resolved'] = True
    match['winner'] = winner

    for bet in match['bets']:
        if bet['side'] == winner:
            odds = match['oddsA'] if winner == 'a' else match['oddsB']
            winnings = int(bet['amount'] * odds)
            uid = bet['user']
            data['users'][uid] = data['users'].get(uid, 1000) + winnings

    save_data(data)
    winner_name = match['playerA'] if winner == 'a' else match['playerB']
    line = match['moneylineA'] if winner == 'a' else match['moneylineB']
    await ctx.send(f"🏆 Winner: {winner_name} ({line}) — payouts sent.")

@commands.has_permissions(administrator=True)
@bot.command()
async def cancel_match(ctx, match_id: int):
    data = load_data()
    if str(match_id) not in data['matches']:
        return await ctx.send("Match ID not found.")

    match = data['matches'][str(match_id)]
    for bet in match['bets']:
        uid = bet['user']
        data['users'][uid] = data['users'].get(uid, 1000) + bet['amount']

    del data['matches'][str(match_id)]
    save_data(data)
    await ctx.send(f"❌ Match {match_id} canceled. Bets refunded.")

@bot.command()
async def matches(ctx):
    data = load_data()
    msg = "**📋 Active Matches:**\n"
    for mid, match in data['matches'].items():
        if not match['resolved']:
            msg += f"ID {mid}: {match['playerA']} ({match['moneylineA']}) vs {match['playerB']} ({match['moneylineB']})\n"
    await ctx.send(msg or "No active matches.")

@bot.command()
async def top(ctx):
    data = load_data()
    leaderboard = sorted(data['users'].items(), key=lambda x: x[1], reverse=True)
    msg = "**🏆 Leaderboard:**\n"
    for i, (uid, bal) in enumerate(leaderboard[:10]):
        user = await bot.fetch_user(int(uid))
        msg += f"{i+1}. {user.name} - ${bal}\n"
    await ctx.send(msg)

@commands.has_permissions(administrator=True)
@bot.command()
async def reset_balances(ctx):
    data = load_data()
    for uid in data['users']:
        data['users'][uid] = 1000
    save_data(data)
    await ctx.send("Balances reset to $1000.")

@bot.command()
async def set_balance(ctx, user: discord.User, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("🚫 You are not authorized to use this command.")
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return await ctx.send("🚫 This command can only be used in the authorized admin channel.")

    data = load_data()
    data['users'][str(user.id)] = amount
    save_data(data)
    await ctx.send(f"✅ {user.name}'s balance set to ${amount}.")

bot.run("YOUR_BOT_TOKEN_HERE")
