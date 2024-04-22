# Импортирую всё необходимое
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
import sqlite3
#создаю базу данных
db = sqlite3.connect('library.db')
cur = db.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS books 
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 title TEXT NOT NULL,
                 author TEXT NOT NULL,
                 description TEXT,                 genre TEXT NOT NULL)
                ''')
db.commit()
storage = MemoryStorage()
API_TOKEN = '7175491792:AAG4Ro8eXH61SQcqfY3T6UVQeUcfGyW-eaM'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())
#Создаю состояния
class ProfileStatesGroup(StatesGroup):
    title = State()
    author = State()
    description = State()
    genre = State()
    search = State()
#создаю Keyboard клавиатуру
keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
button_add_book = KeyboardButton('Добавить книгу')
button_view_books = KeyboardButton('Список всех книг')
button_delete_book = KeyboardButton('Удалить книгу')
button_search_book = KeyboardButton('Поиск книги')
keyboard.add(button_add_book)
keyboard.add(button_view_books)
keyboard.add(button_delete_book)
keyboard.add(button_search_book)
#Обработчик на команду /start
@dp.message_handler(commands=['start'], state = '*' )
async def start(message: types.Message):
    await message.answer("Привет! Я бот-библиотекарь. Чем могу помочь?", reply_markup=keyboard)


@dp.message_handler(text='Поиск книги', state='*')
async def search_book(message: types.Message):
    await message.answer("Введите название, автора либо жанр книги для её поиска!")
    await ProfileStatesGroup.search.set()


@dp.message_handler(state=ProfileStatesGroup.search)
async def process_search(message: types.Message, state: FSMContext):
    search_query = message.text
    cur.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?",
                ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'))
    search_results = cur.fetchall()

    if not search_results:
        await message.answer("По вашему запросу ничего не найдено.")
    else:
        search_results_button = InlineKeyboardMarkup()
        for book in search_results:
            search_results_button.add(InlineKeyboardButton(text=book[1], callback_data=f"book_{book[0]}"))

        await message.answer("Результаты поиска:", reply_markup=search_results_button)

    await state.finish()

#обработчик на добавление пользователем новой книги
@dp.message_handler(text=['Добавить книгу'], state = '*' )
async def add_book(message: types.Message):
    await message.answer("Введите название книги")
    await ProfileStatesGroup.title.set()
#Обработчики на сообщения от пользователя (название, автор, описание, жанр книги)
@dp.message_handler(state=ProfileStatesGroup.title)
async def process_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['title'] = message.text
    await message.answer("Введите автора книги")
    await ProfileStatesGroup.author.set()

@dp.message_handler(state=ProfileStatesGroup.author)
async def process_author(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['author'] = message.text
    await message.answer("Введите описание книги")
    await ProfileStatesGroup.description.set()

@dp.message_handler(state=ProfileStatesGroup.description)
async def process_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
        genre_keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
        #Добавляю клавиатуру чтобы пользователь выбрал предложенный жанр либо написал свой
        button_genre1 = KeyboardButton('Фэнтези')
        button_genre2 = KeyboardButton('Роман')
        button_genre3 = KeyboardButton('Юмор')
        button_genre4 = KeyboardButton('Книги о психологии')
        button_genre5 = KeyboardButton('Детектив')
        button_genre6 = KeyboardButton('Документальная литература')
        genre_keyboard.add(button_genre1).add(button_genre2).add(button_genre3).add(button_genre4).add(button_genre5).add(button_genre6)
    await message.answer("Введите жанр книги, если в предложенном списке жанров нет нужного вам, то напишите свой вариант", reply_markup=genre_keyboard)
    await ProfileStatesGroup.genre.set()

@dp.message_handler(state=ProfileStatesGroup.genre)
async def process_genre(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['genre'] = message.text
        title = data['title']
        author = data['author']
        description = data['description']
        genre = data['genre']
        cur.execute("INSERT INTO books (title, author, description, genre) VALUES (?, ?, ?, ?)", (title, author, description, genre,))
        db.commit()
        await message.answer("Книга успешно добавлена!", reply_markup=keyboard)
        await state.finish()
#Обработчики выдающие список всех книг(каждая книга расположенна в отдельной Inline кнопке)
@dp.message_handler(text=['Список всех книг'], state='*')
async def view_books(message: types.Message):
    cur.execute("SELECT title, author, id FROM books")
    books = cur.fetchall()
    if not books:
        await message.answer("В библиотеке нет ни одной книги")
    else:
        keyboard = InlineKeyboardMarkup()
        for book in books:
            keyboard.add(InlineKeyboardButton(text=book[0], callback_data=f"book_{book[2]}"))
            print(book[0])
        await message.answer("Выберите книгу из списка:", reply_markup=keyboard)

@dp.callback_query_handler(text_startswith=['book'], state='*')
async def process_book(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    book_id = int(callback_query.data.split('_')[1])
    cur.execute("SELECT title, author, genre, description FROM books WHERE id=?", (book_id,))
    book_details = cur.fetchone()
    if book_details:
        title, author, genre, description = book_details
        book_info = f"Название: {title}\nАвтор: {author}\nЖанр: {genre}\nОписание: {description}"
        await bot.send_message(callback_query.from_user.id, book_info)
    else:
        await bot.send_message(callback_query.from_user.id, "Книга не найдена.")

#Обработчики на удаление книги из базы данных(пользователю отправляется список книг, каждая в отдельной Inline кнопке и после нажатия на книгу она удаляется из базы данных)
@dp.message_handler(text=['Удалить книгу'], state='*')
async def delete_books(message: types.Message):
    cur.execute("SELECT title, author, id FROM books")
    books = cur.fetchall()
    if not books:
        await message.answer("В библиотеке нет ни одной книги")
    else:
        keyboard = InlineKeyboardMarkup()
        for book in books:
            keyboard.add(InlineKeyboardButton(text=book[0], callback_data=f"delbook_{book[2]}"))
        await message.answer("Выберите книгу для удаления:", reply_markup=keyboard)

@dp.callback_query_handler(text_startswith=['delbook'], state='*')
async def process_book_delete(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    book_id = int(callback_query.data.split('_')[1])
    cur.execute("SELECT title, author, genre, description FROM books WHERE id=?", (book_id,))
    book_details = cur.fetchone()
    if book_details:
        title, author, genre, description = book_details
        cur.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        await bot.send_message(callback_query.from_user.id, f"Книга '{title}' успешно удалена.")
    else:
        await bot.send_message(callback_query.from_user.id, "Книга не найдена.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)