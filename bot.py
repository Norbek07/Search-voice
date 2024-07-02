from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart,Command
from aiogram import F
from aiogram.types import Message,InlineQuery,InlineKeyboardButton,InlineQueryResultArticle,InputTextMessageContent,InlineQueryResultPhoto,InlineQueryResultCachedVoice
# from aiogram.types.inline_query_result_photo import InlineQueryResultType
from search_images import fetch_inline_search_images
from data import config
import asyncio
import logging
import sys
from menucommands.set_bot_commands  import set_default_commands
from baza.sqlite import Database
from filters.admin import IsBotAdminFilter
from filters.check_sub_channel import IsCheckSubChannels
from keyboard_buttons import admin_keyboard
from aiogram.fsm.context import FSMContext #new
from states.reklama import Adverts, AudioState
from aiogram.utils.keyboard import InlineKeyboardBuilder
import time 
ADMINS = config.ADMINS
TOKEN = config.BOT_TOKEN
CHANNELS = config.CHANNELS

dp = Dispatcher()




@dp.message(CommandStart())
async def start_command(message:Message):
    full_name = message.from_user.full_name
    telegram_id = message.from_user.id
    try:
        db.add_user(full_name=full_name,telegram_id=telegram_id)
        await message.answer(text="Assalomu alaykum, botimizga hush kelibsiz")
    except:
        await message.answer(text="Assalomu alaykum")

#help commands
@dp.message(Command("help"))
async def help_commands(message:Message):
    await message.answer("Sizga qanday yordam kerak")



#about commands
@dp.message(Command("about"))
async def about_commands(message:Message):
    await message.answer("Bot sizga qiziqarli ovozlarni yuklab beradi!")

# import pprint
# @dp.message()
# async def get_file_id(message:Message):
#     audio_id = message.voice.file_id
#     # pprint.pprint(audio_id)
#     await message.answer(f"file_id = {audio_id}")


@dp.inline_query()
async def inline_voice_search(inline_query: InlineQuery):
    title = inline_query.query
    audiolar = await db.search_audios_title(title)

    results = [
        InlineQueryResultCachedVoice(
            id=f"{audio[0]}",
            voice_file_id=audio[1],
            title=audio[2]
        ) for audio in audiolar[:10]
    ]
    await inline_query.answer(results=results)
    

@dp.inline_query()
async def inline_search(inline_query: InlineQuery):
    
    #artikl yuborish
    # result =[
    #     InlineQueryResultArticle(
    #         id="1",
    #         title="Sifat",
    #         input_message_content=InputTextMessageContent(
    #             message_text="Bu sifat o'quv markazi. Navoiyda joylashgan"
    #         ),
    #         description="Ajoyib o'quv markazi"
    #     ),
    #     InlineQueryResultArticle(
    #         id="2",
    #         title="IT IELTS SCHOOL",
    #         input_message_content=InputTextMessageContent(
    #             message_text="Bu IT IELTS SCHOOL o'quv markazi. Navoiyda joylashgan"
    #         ),
    #         description="THE BEST"
    #     )
    # ]

    try:
        text = inline_query.query
        photos = await fetch_inline_search_images(text, count=20)

        results = [
            InlineQueryResultPhoto(
                id=str(i),
                photo_url=img,
                thumbnail_url=img
            )
            for i, img in enumerate(photos)
        ]

        await inline_query.answer(results=results)

    except Exception as e:
        print(f"Xatolik: {e}")



@dp.message(IsCheckSubChannels())
async def kanalga_obuna(message:Message):
    text = ""
    inline_channel = InlineKeyboardBuilder()
    for index,channel in enumerate(CHANNELS):
        ChatInviteLink = await bot.create_chat_invite_link(channel)
        inline_channel.add(InlineKeyboardButton(text=f"{index+1}-kanal",url=ChatInviteLink.invite_link))
    inline_channel.adjust(1,repeat=True)
    button = inline_channel.as_markup()
    await message.answer(f"{text} kanallarga azo bo'ling",reply_markup=button)



@dp.message(Command("admin"),IsBotAdminFilter(ADMINS))
async def is_admin(message:Message):
    await message.answer(text="Admin menu",reply_markup=admin_keyboard.admin_button)


@dp.message(F.text=="Foydalanuvchilar soni",IsBotAdminFilter(ADMINS))
async def users_count(message:Message):
    counts = db.count_users()
    text = f"Botimizda {counts[0]} ta foydalanuvchi bor"
    await message.answer(text=text)

@dp.message(F.text=="Reklama yuborish",IsBotAdminFilter(ADMINS))
async def advert_dp(message:Message,state:FSMContext):
    await state.set_state(Adverts.adverts)
    await message.answer(text="Reklama yuborishingiz mumkin !")

@dp.message(Adverts.adverts)
async def send_advert(message:Message,state:FSMContext):
    
    message_id = message.message_id
    from_chat_id = message.from_user.id
    users = db.all_users_id()
    count = 0
    for user in users:
        try:
            await bot.copy_message(chat_id=user[0],from_chat_id=from_chat_id,message_id=message_id)
            count += 1
        except:
            pass
        time.sleep(0.5)
    
    await message.answer(f"Reklama {count}ta foydalanuvchiga yuborildi")
    await state.clear()



#audio qo'shish

@dp.message(F.text=="audio qo'shish",IsBotAdminFilter(ADMINS))
async def auido_adds(message:Message,state:FSMContext):
    await message.answer("Audio nomini kiriting")
    await state.set_state(AudioState.title)

@dp.message(F.text,AudioState.title)
async def auido_title(message:Message,state:FSMContext):
    await message.answer("Audio yuboring")
    title = message.text
    await state.set_state(AudioState.voice_file_id)
    await state.update_data(title=title)

@dp.message(F.voice,AudioState.voice_file_id)
async def auido_voice(message:Message,state:FSMContext):
    data = await state.get_data()
    title = data.get("title")
    voice_file_id = message.voice.file_id
    db.add_audio(voice_file_id=voice_file_id,title=title)

    await message.answer("Audio muvaffaqiyatli bazaga qo'shildi")
    await state.clear()


@dp.startup()
async def on_startup_notify(bot: Bot):
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=int(admin),text="Bot ishga tushdi")
        except Exception as err:
            logging.exception(err)

#bot ishga tushganini xabarini yuborish
@dp.shutdown()
async def off_startup_notify(bot: Bot):
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=int(admin),text="Bot ishdan to'xtadi!")
        except Exception as err:
            logging.exception(err)


def setup_middlewares(dispatcher: Dispatcher, bot: Bot) -> None:
    """MIDDLEWARE"""
    from middlewares.throttling import ThrottlingMiddleware

    # Spamdan himoya qilish uchun klassik ichki o'rta dastur. So'rovlar orasidagi asosiy vaqtlar 0,5 soniya
    dispatcher.message.middleware(ThrottlingMiddleware(slow_mode_delay=0.5))



async def main() -> None:
    global bot,db
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    db = Database(path_to_db="data/main.db")
    db.create_table_users()
    db.create_table_audios()
    await set_default_commands(bot)
    await dp.start_polling(bot)
    setup_middlewares(dispatcher=dp, bot=bot)




if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    asyncio.run(main())