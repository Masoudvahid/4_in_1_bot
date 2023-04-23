from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
import aiohttp
import requests
import configparser
import logging


config = configparser.ConfigParser()
config.read('config.ini')

TELEGRAM_TOKEN = config['TOKENS']['TELEGRAM']
WEATHER_TOKEN = config['TOKENS']['WEATHER']
CAT_TOKEN = config['TOKENS']['CAT']

# Create a new bot instance
bot = Bot(token=TELEGRAM_TOKEN)
# Create a new dispatcher instance
dp = Dispatcher(bot, storage=MemoryStorage())


# Define a function to greet the user and prompt them to select a specific bot function
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weather_button = types.KeyboardButton('Get Weather')
    currency_button = types.KeyboardButton('Convert Currency')
    cute_animals_button = types.KeyboardButton('Send Cute Animals')
    poll_button = types.KeyboardButton('Create Poll')
    keyboard_markup.add(weather_button, currency_button, cute_animals_button, poll_button)
    await message.reply("Hi! my name is 4 in 1.\nWhat would you like me to do?", reply_markup=keyboard_markup)


class StatesForm(StatesGroup):
    city = State()
    currency = State()
    poll_questions = State()
    poll_options = State()


@dp.message_handler(lambda message: message.text == 'Get Weather')
async def get_weather(message: types.message):
    await message.reply("Please enter the name of a city")

    # Set the state to 'city'
    await StatesForm.city.set()


@dp.message_handler(state=StatesForm.city)
async def process_weather(message: types.Message, state: FSMContext):
    city = message.text
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_TOKEN}") as resp:
            if resp.status == 200:
                data = await resp.json()
                temp = data['main']['temp']
                await message.answer(f"The temperature in {city} is {temp} K.")
            else:
                await message.answer("Sorry, I could not find the weather for that city.")

    # Reset the state to None
    await state.finish()


# Define a function to convert currencies using the public exchange rate API
@dp.message_handler(lambda message: message.text == 'Convert Currency')
async def convert_currency(message: types.Message):
    await message.reply("Please enter the amount, source and target, currency you wish to convert seperated by spaces.")

    # Set the state to 'currency_amount'
    await StatesForm.currency.set()


@dp.message_handler(state=StatesForm.currency)
async def process_currency(message: types.Message, state: FSMContext):
    try:
        amount, from_currency, to_currency = message.text.split()
        if not amount.isdigit():
            await message.reply(
                "Amount should be number, try again!")
            return

        url = f'https://api.exchangerate-api.com/v4/latest/{from_currency}'
        response = requests.get(url).json()

    except ValueError:
        await message.reply(
            "Invalid format. Please enter the amount, followed by the source and target currencies, separated by spaces.")
        return
    except Exception as err:
        logging.error(f"Unexpected {err=}, {type(err)=}")
        return

    try:
        conversion_rate = response['rates'][to_currency.upper()]
    except KeyError:
        await message.reply("Invalid currency format.")
        return await state.finish()

    converted_amount = float(amount) * conversion_rate
    await message.reply(f"{amount} {from_currency} is equal to {converted_amount} {to_currency}.")

    # Reset the state to None
    await state.finish()


# Define a function to send a random picture of cute animals
@dp.message_handler(lambda message: message.text == 'Send Cute Animals')
async def cute_cat(message: types.Message):
    try:
        url = "https://api.thecatapi.com/v1/images/search"
        response = requests.get(url, headers={'x-api-key': f'{CAT_TOKEN}'}).json()
        image_url = response[0]['url']
    except Exception as err:
        logging.error(f"Unexpected {err=}, {type(err)=}")
        return
    await bot.send_photo(chat_id=message.chat.id, photo=image_url)


# # Define a function to create polls and send them to a group chat with a specific question and answer options
@dp.message_handler(lambda message: message.text == 'Create Poll')
async def create_poll(message: types.Message):
    # Ask the user for the question and answer options
    await message.reply("Please enter the question for the poll:")

    await StatesForm.poll_questions.set()


@dp.message_handler(state=StatesForm.poll_questions)
async def get_question(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['question'] = message.text

    await message.reply("Please enter the answer options, separated by |")
    await StatesForm.next()


@dp.message_handler(state=StatesForm.poll_options)
async def get_question(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['options'] = message.text.split('|')

        # Polls with one option is prohibited
        if len(data['options']) < 2:
            await message.reply("Poll should have at least two options. Try again!")
            return

    await bot.send_poll(chat_id=message.chat.id, question=data['question'], options=data['options'])


@dp.message_handler()
async def enter_valid_command(message: types.Message):
    await message.reply(f"Please chose one of the valid commands via the keyboard")


# Start the bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
