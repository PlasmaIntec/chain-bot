# bot.py
import os
import random
import re
import threading
import asyncio
import time
import sched
from datetime import datetime
from pytz import timezone
import pytz

import discord
from dotenv import load_dotenv
from generate_wordcloud import generate_wordcloud

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

@client.event
async def on_ready():
	print("bot ready")

reference_referrer_pairs = [(755811907948118179, 741321254027526195), (726866762523738202, 743540914336694392)]

@client.event
async def on_message(message):
	print(message.content, message.author)
	if message.author == client.user:
		return

	if message.author.id == 268478587651358721: # check if MonitoRSS posted a new livestream episode
		match = re.match(r".*Bret and Heather (.*) DarkHorse Podcast Livestream.*", message.content)
		if match:
			live_stream = match[1]
			live_stream_number = int("".join(e for e in live_stream if e.isnumeric()))
			episode_name = "episode-%s" % live_stream_number
			channel = discord.utils.get(client.get_all_channels(), name=episode_name)
			category = await client.fetch_channel(800076391156547634) # category: Episode Discussions
			if not channel:
				new_channel = await message.guild.create_text_channel(episode_name, category=category)
				print("CREATE CHANNEL: ", new_channel)

	match = re.match(r"https://discord(app)?\.com/channels/(\d+)/(\d+)/(\d+)", message.content)
	if match:
		guild_id, channel_id, message_id = match[2], match[3], match[4]
		if (int(channel_id), message.channel.id) in reference_referrer_pairs:
			print("detected cross channel reference")
			ref_channel = await client.fetch_channel(channel_id)
			ref_msg = await ref_channel.fetch_message(message_id)
			if ref_msg.author.id != message.author.id:
				msg = "<@!%s> you have been summoned by <@!%s> " % (ref_msg.author.id, message.author.id)
				await message.channel.send(msg)

	match = re.match(r".*lab leak theory.*", message.content.lower())
	if match:
		print("detected theory reference")
		msg = "<@!%s> do you mean lab leak hypothesis?" % (message.author.id)
		await message.channel.send(msg)

	if message.content.startswith("!wordcloud"):
		print("generating wordcloud for channel %s" % message.channel.name)
		channel = await client.fetch_channel(message.channel.id)
		await generate_wordcloud_for_channel(channel)

	match = re.match(r"!name (.*)", message.content.lower())
	if match:
		name = match[1]
		print("detected channel name change")
		msg = "changing channel name <#%s> -> %s" % (message.channel.id, name)
		await message.channel.send(msg)
		await message.channel.edit(name=name)
		msg = "channel name changed to %s" % (message.channel.name)
		await message.channel.send(msg)

async def generate_wordcloud_for_channel(channel):	
	messages = []

	async for message in channel.history(limit=200):
		if message.author != client.user:
			messages.append(message.content)

	text = "".join(messages)
	wordcloud = generate_wordcloud(text)
	wordcloud.to_file("wordcloud.jpg")
	with open('wordcloud.jpg', 'rb') as fp:
		await channel.send(file=discord.File(fp, 'wordcloud.jpg'))

# @client.event
# async def on_raw_message_delete(message):
# 	print("detected raw message delete")
# 	print(message)
# 	if message.cached_message:
# 		id = message.cached_message.author.id
# 		user = await client.fetch_user(id)
# 		await user.send("beep boop: your message in the <#%s> channel was deleted" % message.channel_id)

async def check_time():
	print("running check_time")
	await client.wait_until_ready()
	print("ready check_time")
	while not client.is_closed():
		try:
			print("scheduling check_time")
			utc_now = pytz.utc.localize(datetime.utcnow())
			current_time = utc_now.astimezone(pytz.timezone("US/Eastern"))
			current_day = datetime.today().weekday()
			print("current time is %s, weekday is %s" % (current_time.strftime("%H:%M:%S"), current_day))
			channel = await client.fetch_channel("776116999520649248") # CHAT OVERFLOW / CAMPFIRE KAROAKE VOICE CHANNEL
			name = "Campfire Karaoke" if current_day == 0 and ((current_time.hour == 19 and current_time.minute >= 45) or (20 <= current_time.hour < 22) or (current_time.hour == 22 and current_time.minute <= 15)) else "Chat Overflow"
			await channel.edit(name=name)
			print("updated channel name to %s" % name)
			await asyncio.sleep(60)
		except Exception as e:
			print(e)
			await asyncio.sleep(60)
	print("done check_time")

def wait():
	print("execute wait")
	asyncio.run_coroutine_threadsafe(check_time(), asyncio.new_event_loop())

client.loop.create_task(check_time())

client.run(TOKEN)