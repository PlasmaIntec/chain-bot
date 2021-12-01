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

async def archive_channel_to_archive(channel_id, archive_id):
	old_channel = await client.fetch_channel(channel_id)
	archive_channel = await client.fetch_channel(archive_id)
	print("ARCHIVING CHANNEL: " + old_channel.name)
	old_channel.edit(category=archive_channel, sync_permissions=True) # requires Manage Channel + Manage Permissions permissions

@client.event
async def on_message(message):
	print(message.content, message.author)
	if message.author == client.user:
		return

	if message.author.id == 268478587651358721: # check if MonitoRSS posted a new livestream episode
		match = re.match(r".*Bret and Heather (.*) DarkHorse Podcast Livestream.*(https\:\/\/odysee\.com\/.*)", message.content, re.S)
		print("MATCH: " + match[0])
		if match:
			livestream, livestream_link = match[1], match[2]
			print("LINK: " + livestream_link)
			livestream_number = int("".join(e for e in livestream if e.isnumeric()))
			episode_name = "episode-%s" % livestream_number
			channel = discord.utils.get(client.get_all_channels(), name=episode_name)
			darkhorse_podcast_category_id = 833086830521483324
			category = await client.fetch_channel(darkhorse_podcast_category_id)
			if not channel:
				# if channel isn't created yet, create new discussion channel, post livestream link, then pin livestream link
				new_channel = await message.guild.create_text_channel(episode_name, category=category)
				print("CREATE CHANNEL: ", new_channel)
				message = await new_channel.send(livestream_link)
				print(message)
				await message.pin(reason="livestream link")
				
			# archive old channels in episode discussions category
			episode_discussions_channel = await client.fetch_channel(darkhorse_podcast_category_id)
			archive_id = 810266760934326332 # podcast archives category
			archive_channel = await client.fetch_channel(archive_id)

			for channel in episode_discussions_channel.channels:
				if channel.name.startswith("episode-") and (datetime.utcnow()-channel.created_at).days > 13:
					print("ARCHIVING CHANNEL: " + channel.name)
					await channel.edit(category=archive_channel, sync_permissions=True)

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
			reset_channel_ids_and_names = [
				["833087132414771310", "Lounge One"],
				["732987976317009922", "lounge-one-text"],
				["833087155546620005", "Lounge Two"],
				["804431468662358057", "lounge-two-text"],
				["838114202979532830", "Seminar Room"],
			]
			if current_time.hour == 0: # reset channel names each day at midnight
				for id, name in reset_channel_ids_and_names:
					channel = await client.fetch_channel(id)
					await channel.edit(name=name)
				print("updated lounge channel names at midnight")
			# if current_day == 6 and ((current_time.hour == 19 and current_time.minute >= 30) or (20 <= current_time.hour < 22) or (current_time.hour == 22 and current_time.minute <= 15)): # between 4:30 and 7:15 PST
			# 	await lounge_two_channel.edit(name="Campfire Karaoke")
			# 	print("updated Lounge Two channel name to Campfire Karaoke")
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