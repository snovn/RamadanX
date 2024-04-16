import os
import discord
from discord import app_commands
from discord.app_commands import Group, command
import requests
from discord.ext import commands
from hijri_converter import convert
from typing import List
import math
import random
import aiohttp
import time
from dotenv import load_dotenv
from discord import FFmpegPCMAudio
import asyncio
from PIL import Image, ImageOps
import io


load_dotenv()

hijri_date = convert.Gregorian.today().to_hijri()

islamic_group = Group(name='random', description='Randomized commands')
intents = discord.Intents.default()
client = discord.Client(intents=intents)

tree = app_commands.CommandTree(client)

API_URL = 'https://muslimsalat.com/{0}.json?key={1}'

PRAYER_API_KEY = os.environ.get('PRAYER_TIMES_API_KEY')

queues = {}
currently_playing = {}


is_playing = False


@client.event
async def on_ready():
  try:        
    await tree.sync()
    print(f'Synced')
  except Exception as e:
    print(e)
  await client.change_presence(activity=discord.Game(name="Ramadan Kareem! 🌙"))
  print(f'Logged in as {client.user.name}')




@client.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.CommandNotFound):
    pass
  else:
    raise error




@tree.command(name='verse', description="Sends a specific verse from the Quran")
@app_commands.describe(verse="The format 'verse:chapter' when indicating usage. For example, 1:1", language="Please choose the translation language.")
@app_commands.choices(language=[
    app_commands.Choice(name="Arabic", value="ar.alafasy"),
    app_commands.Choice(name="English", value="en.asad"),
    ])
async def get_specific_verse(interaction: discord.Interaction, verse: str, language: app_commands.Choice[str]):

    cache_buster = int(time.time()) + random.randint(1, 1000)
    edition = language.value
    url = f"https://api.alquran.cloud/v1/ayah/{verse}/{edition}?{cache_buster}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                ayah = data['data']['text']
                surah_name = data['data']['surah']['englishName']
                ayah_number = data['data']['numberInSurah']
                juz_number = data['data']['juz']

                embed = discord.Embed(title=f"Verse from the Quran",
                                      color=discord.Color.green())
                embed.add_field(
                    name=f"Surah {surah_name} - Ayah {ayah_number} - Juz {juz_number} ({language.name})",
                    value=ayah,
                    inline=False)
                embed.set_footer(text="Quran API")
                await interaction.response.send_message(embed=embed)

    except aiohttp.ClientError as e:
        await interaction.response.send_message("Verse not found. Please type /help for usage!", ephemeral=True)


@islamic_group.command(name='hadith', description='Sends a random hadith from Sahih Muslim')
async def hadith(interaction: discord.Interaction):
    # Define a function to fetch a random Hadith
    async def get_random_hadith():
        hadith_number = random.randint(1, 2000)  # 4930 is the maximum number of Hadith available
        url = f"https://api.hadith.gading.dev/books/muslim/{hadith_number}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    hadith_data = await response.json()
                    return hadith_data['data']['contents']
                else:
                    return None

    hadith = await get_random_hadith()

    if hadith:
        embed = discord.Embed(title="A Random Hadith from Sahih Muslim", color=discord.Color.gold())
        embed.add_field(name="Hadith Number", value=hadith['number'], inline=False)

        # Truncate the Hadith content if it exceeds 1024 characters
        hadith_content = hadith['arab'][:1021] + "..." if len(hadith['arab']) > 1024 else hadith['arab']
        embed.add_field(name="Hadith Content", value=f"*{hadith_content}*", inline=False)

        embed.set_footer(text="May Allah's peace and blessings be upon His Messenger.")

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Failed to fetch Hadith", ephemeral=True)

@islamic_group.command(name='verse', description='Sends a random verse from the Quran')
async def get_random_verse(interaction: discord.Interaction):
    cache_buster = int(time.time()) + random.randint(1, 4000)
    url = f"https://api.alquran.cloud/v1/ayah/random?_={cache_buster}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                surah_name = data['data']['surah']['englishName']
                surah_number = data['data']['surah']['number']
                ayah_number = data['data']['numberInSurah']
                juz_number = data['data']['juz']
                ayah_text = data['data']['text']

                image_url = f"https://cdn.islamic.network/quran/images/{surah_number}_{ayah_number}.png"

                async with session.get(image_url) as image_response:
                    image_response.raise_for_status()
                    image_bytes = await image_response.read()
                    image = Image.open(io.BytesIO(image_bytes))

                    # Add a white background to the image
                    image_with_white_bg = ImageOps.expand(image, border=(10, 10), fill='white')

                    # Save the image with white background to a temporary file
                    with io.BytesIO() as image_buffer:
                        image_with_white_bg.save(image_buffer, format='PNG')
                        image_buffer.seek(0)

                        # Send the image with white background in Discord embed
                        file = discord.File(image_buffer, filename='verse.png')
                        embed = discord.Embed(title=f"Random Verse from the Quran",
                                            color=discord.Color.green())
                        embed.set_image(url="attachment://verse.png")
                        embed.add_field(name="Surah", value=f"{surah_name} ({surah_number})", inline=False)
                        embed.add_field(name="Ayah", value=ayah_number, inline=True)
                        embed.add_field(name="Juz", value=juz_number, inline=True)
                        embed.add_field(name="Verse Text", value=ayah_text, inline=False)
                        embed.set_footer(text="Provided by RamadanX", icon_url="https://cdn.discordapp.com/avatars/1085670814558461962/e72290cd3bbb0700ad30a354f53d77fd.webp")
                        await interaction.response.defer()
                        await asyncio.sleep(1)  # Wait for 1 second
                        await interaction.followup.send(embed=embed, file=file)
    except (aiohttp.ClientError, KeyError, IOError) as e:
        await interaction.response.send_message("An error occurred while fetching the verse.", ephemeral=True)

@tree.command(name='help', description="Sends a list with all the commands usage")
async def show_help(ctx):
  embed = discord.Embed(title="Ramadan Bot Help", color=discord.Color.gold())
  embed.add_field(name="r!prayer <city>",
                  value="Get prayer times for the specified city.",
                  inline=False)
  embed.add_field(name="r!qibla <city>",
                  value="Get the Qibla direction based on the specified city.",
                  inline=False)
  embed.add_field(name="r!hijri",
                  value="Get the current date in the Hijri calendar.",
                  inline=False)
  await ctx.send(embed=embed)

@tree.command(name='prayer', description="Sends times of prayers in a specific region")
@app_commands.describe(city="Please provide a valid city value.")
async def get_prayer_times(interaction: discord.Interaction, city: str):
    formatted_city = city.title()
    url = API_URL.format(formatted_city, PRAYER_API_KEY)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await interaction.response.send_message("City not found. Please make sure to type the city name correctly!", ephemeral=True)
                return

            data = await response.json()

            if data.get('status_valid') == 1:
                prayer_times = data['items'][0]
                country = data['country']

                fajr_time = prayer_times['fajr']
                sunrise_time = prayer_times['shurooq']
                dhuhr_time = prayer_times['dhuhr']
                asr_time = prayer_times['asr']
                maghrib_time = prayer_times['maghrib']
                isha_time = prayer_times['isha']

                embed = discord.Embed(
                    title=f"Today's Prayer Times in **{formatted_city}**, **{country}**",
                    color=discord.Color.gold())
                embed.add_field(name=":mosque: Fajr", value=fajr_time, inline=True)
                embed.add_field(name=":sunrise: Sunrise",
                                value=sunrise_time,
                                inline=True)
                embed.add_field(name=":mosque: Dhuhr", value=dhuhr_time, inline=True)
                embed.add_field(name=":mosque: Asr", value=asr_time, inline=True)
                embed.add_field(name=":mosque: Maghrib", value=maghrib_time, inline=True)
                embed.add_field(name=":mosque: Isha", value=isha_time, inline=True)
                embed.set_image(
                    url="https://i.ibb.co/YXMHpr5/1000-F-205496703-r-BAGr-T1eqm-SH9-Y1v-IQAn-Z7-C5-W6-RInn-YV-transformed.png"
                )
                embed.set_footer(text=f"Today's Hijri date is: {hijri_date}")
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("City not found. Please make sure to type the city name correctly!", ephemeral=True)


@tree.command(name='qibla', description="Sends the direction of the Kaaba")
@app_commands.describe(city="Please provide a valid area.")
async def get_qibla_direction(interaction: discord.Interaction, city: str):
    formatted_city = city.title()
    url = API_URL.format(formatted_city, PRAYER_API_KEY)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await interaction.response.send_message("Failed to retrieve data for the provided city.", ephemeral=True)
                return

            data = await response.json()

            if data.get('status_valid') != 1:
                await interaction.response.send_message("Invalid city name provided.", ephemeral=True)
                return

            # Proceed with the calculation
            latitude = float(data['latitude'])
            longitude = float(data['longitude'])

            # Calculate qibla direction
            KAABA_LAT = 21.422487
            KAABA_LONG = 39.826206
            d_long = math.radians(KAABA_LONG - longitude)

            num = math.sin(d_long) * math.cos(math.radians(KAABA_LAT))
            den = (
                math.cos(math.radians(latitude)) * math.sin(math.radians(KAABA_LAT)) -
                math.sin(math.radians(latitude)) * math.cos(math.radians(KAABA_LAT)) *
                math.cos(d_long))
            qibla_direction = math.degrees(math.atan2(num, den))

            qibla_direction = (qibla_direction + 360) % 360

            embed = discord.Embed(
                title=f"Qibla Direction",
                description=f"The Qibla direction for **{formatted_city}** is **{qibla_direction:.2f}°**",
                color=0x3498db  # Blue color
            )
            embed.set_thumbnail(url='https://i.ibb.co/wdbzMcn/compass.png')
            embed.set_footer(text="Provided by RamadanX", icon_url="https://cdn.discordapp.com/avatars/1085670814558461962/e72290cd3bbb0700ad30a354f53d77fd.webp")

            await interaction.response.send_message(embed=embed)

    formatted_city = city.title()
    url = API_URL.format(formatted_city, PRAYER_API_KEY)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await interaction.response.send_message("Failed to retrieve data for the provided city.", ephemeral=True)
                return

            data = await response.json()

            if data.get('status_valid') != 1:
                await interaction.response.send_message("Invalid city name provided.", ephemeral=True)
                return

            # Proceed with the calculation
            latitude = float(data['latitude'])
            longitude = float(data['longitude'])

            # Calculate qibla direction
            KAABA_LAT = 21.422487
            KAABA_LONG = 39.826206
            d_long = math.radians(KAABA_LONG - longitude)

            num = math.sin(d_long) * math.cos(math.radians(KAABA_LAT))
            den = (
                math.cos(math.radians(latitude)) * math.sin(math.radians(KAABA_LAT)) -
                math.sin(math.radians(latitude)) * math.cos(math.radians(KAABA_LAT)) *
                math.cos(d_long))
            qibla_direction = math.degrees(math.atan2(num, den))

            qibla_direction = (qibla_direction + 360) % 360

            embed = discord.Embed(
                title=f"Qibla direction for {formatted_city}",
                description=f"**{qibla_direction:.2f}°**",
                color=0x00ff00  # You can customize the color
            )

            await interaction.response.send_message(embed=embed)



tree.add_command(islamic_group)
client.run(os.environ.get('DISCORD_BOT_TOKEN'))
