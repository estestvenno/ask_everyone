import sqlite3
from random import sample

import requests
import urllib.parse as urlparse

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from bs4 import BeautifulSoup
from aiogram.dispatcher.filters import Text, state
from aiogram.utils import executor, markdown
from aiogram.utils.exceptions import MessageNotModified
from forbidden_words import forbidden_words

from config import TOKEN
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

con = sqlite3.connect('ask_everyones.db')
cur = con.cursor()

tags = ['📰Новости', '📱Блоги', '💻Технологии', '🤡Юмор', '💼Политика', '💵Финансы', '👨‍🏫Наука и образование',
        '🎸Музыка', '🕶Бизнес', '📊Маркетинг', '🎥Фильмы и сериалы', '📚Книги', '🏀Здоровье и спорт', '🗺Путешествия',
        '🌄Искусство', '🥼Мода', '💊Медицина', '🎮Игры', '🍕Еда', '🪡Рукоделие', '🧩Другое']

tags_db = ['news', 'blog', 'technologies', 'humor', 'politics', 'finance', 'science_and_education', 'music', 'business',
           'marketing', 'movies', 'books', 'health_and_sports', 'journeys', 'art', 'fashion', 'medicine', 'games',
           'meal', 'handiwork', 'other']

valid_link = ''

deceptions = {'а': ['а', 'a', '@'],
              'б': ['б', '6', 'b'],
              'в': ['в', 'b', 'v'],
              'г': ['г', 'r', 'g'],
              'д': ['д', 'd'],
              'е': ['е', 'e'],
              'ё': ['ё', 'e'],
              'ж': ['ж', 'zh', '*', '}|{'],
              'з': ['з', '3', 'z'],
              'и': ['и', 'u', 'i'],
              'й': ['й', 'u', 'i'],
              'к': ['к', 'k', 'i{', '|{'],
              'л': ['л', 'l', 'ji'],
              'м': ['м', 'm'],
              'н': ['н', 'h', 'n'],
              'о': ['о', 'o', '0'],
              'п': ['п', 'n', 'p'],
              'р': ['р', 'r', 'p'],
              'с': ['с', 'c', 's'],
              'т': ['т', 'm', 't'],
              'у': ['у', 'y', 'u'],
              'ф': ['ф', 'f'],
              'х': ['х', 'x', 'h', '}{'],
              'ц': ['ц', 'c', 'u,'],
              'ч': ['ч', 'ch'],
              'ш': ['ш', 'sh'],
              'щ': ['щ', 'sch'],
              'ь': ['ь', 'b'],
              'ы': ['ы', 'bi'],
              'ъ': ['ъ'],
              'э': ['э', 'e'],
              'ю': ['ю', 'io'],
              'я': ['я', 'ya']
              }  # словарь для замены символов в проверяемом предложении


class LinkRatings:  # класс для обработки сообщений, не связанных с кнопкой
    def __init__(self, message):
        self.message = message
        self.all_about_link = []
        self.all_about_opinion = []

    def checking_link(self):
        # ссылка проверяется на работоспособность
        if self.message.text[:12] == 'https://t.me':
            if urlparse.urlparse(self.message.text).scheme:
                try:
                    # ссылка открывается и с нее парсятся данные для проверки, что это ссылка на телеграмм канал
                    opening_link = requests.get(self.message.text)
                    checking_for_channel = BeautifulSoup(opening_link.text, features="html.parser")
                    checking_for_channel = \
                    checking_for_channel.find_all('a', attrs={'class': 'tgme_action_button_new'})[0]
                    if str(checking_for_channel.text) == 'View in Telegram':
                        return 'normal'
                    else:
                        return 'this is not a channel'
                except Exception:
                    return 'this is not a channel'
            else:
                return 'this is not a link'
        else:
            return 'this is not a link'

    def creation_in_absence_of(self):
        # в базу данных добавляется ссылка, если ее там нет
        if not cur.execute("SELECT * FROM opinion_about_link WHERE link=?",
                           (self.message.text,)).fetchall():
            cur.execute(
                '''INSERT INTO opinion_about_link
                 VALUES(?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)''',
                (self.message.text,))
            con.commit()
        self.all_about_link = \
            cur.execute("SELECT * FROM opinion_about_link WHERE link=?",
                        (self.message.text,)).fetchall()[0]

        if not cur.execute("SELECT * FROM user_evaluation WHERE estimated_link=? AND user=?",
                           (self.message.text, self.message.from_user.id,)).fetchall():
            cur.execute(
                '''INSERT INTO user_evaluation VALUES(?, ?, 0,
                 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)''',
                (self.message.from_user.id, self.message.text,))
            con.commit()
        self.all_about_opinion = \
            cur.execute("SELECT * FROM user_evaluation WHERE estimated_link=? AND user=?",
                        (self.message.text, self.message.from_user.id,)).fetchall()[0]

    def creating_response(self):
        # создание сообщения бота на отправку ему подходящей ссылки
        rating = cur.execute(f"SELECT AVG(estimation) FROM user_evaluation WHERE estimated_link=?",
                             (self.message.text,)).fetchall()[0][0]
        ready_answer = f'Ссылка: {self.message.text}' \
                       f'\n' \
                       f'\nОбщий рейтинг: {rating}⭐️' \
                       f'\n' \
                       f'\nПрикрепленные теги:'

        for j in range(len(tags)):
            ready_answer += f'\n{tags[j]}:' \
                            f' {self.all_about_link[j + 2]}'
        return ready_answer


class CallbackResponses:  # класс для обработки сообщений, связанных с нажатием кнопки
    def __init__(self, callback):
        self.callback = callback

    def creating_text_click_response(self):
        # Первое сообщение после решения пользователя об оценке ссылки
        return f'Оцениваемая ссылка: {self.callback.data.split()[1]}\n\nПоставьте свою оценку и выберете' \
               f' не более 3 тегов для определения тематики канала'

    def creating_buttons_click_response(self, all_about_link, all_about_opinion):
        # Создание меняющихся кнопок к первому сообщению
        markup = types.InlineKeyboardMarkup()
        list_for_number = []
        for j in range(1, 11):  # цикл создания первых 10 кнопок со звездочками для оценки ссылки
            if j == all_about_opinion[2]:
                # В случае, если пользователем уже выбрана оценка
                list_for_number.append(types.InlineKeyboardButton(text=f'{j}🌟',
                                                                  callback_data=f"general_assessment"
                                                                                f" {self.callback.data.split()[1]}"
                                                                                f" {j}"))
            else:
                # В случае, если пользователем не выбрана оценка
                list_for_number.append(types.InlineKeyboardButton(text=f'{j}⭐️',
                                                                  callback_data=f"general_assessment"
                                                                                f" {self.callback.data.split()[1]}"
                                                                                f" {j}"))
        # добавление кнопок по 5 в ряд
        markup.row(list_for_number[0], list_for_number[1], list_for_number[2], list_for_number[3], list_for_number[4])
        markup.row(list_for_number[5], list_for_number[6], list_for_number[7], list_for_number[8], list_for_number[9])
        list_for_number = []
        for j in range(len(tags)):  # такой же цикл, но уже с возможными категориями
            opinion = all_about_link[j + 2]
            if all_about_opinion[j + 3] == 0:
                list_for_number.append(types.InlineKeyboardButton(text=f'☑️{tags[j]}: {opinion}',
                                                                  callback_data=f"tags_assessment"
                                                                                f" {self.callback.data.split()[1]}"
                                                                                f" {j}"))
            else:
                list_for_number.append(types.InlineKeyboardButton(text=f'✅ {tags[j]}: {opinion}',
                                                                  callback_data=f"tags_assessment"
                                                                                f" {self.callback.data.split()[1]}"
                                                                                f" {j}"))
        for j in range(0, len(list_for_number)):  # Цикл добавления кнопок по 2 в ряд
            if j % 2 == 1:
                markup.row(list_for_number[j - 1], list_for_number[j])
        # создание кнопки для работы отзывом
        if cur.execute("SELECT * FROM user_reviews WHERE link=?  AND user=?",
                       (self.callback.data.split()[1], self.callback.from_user.id,)).fetchall():
            markup.row(types.InlineKeyboardButton(text='🗑Удалить свой отзыв',
                                                  callback_data=f"deleting_review"
                                                                f" {self.callback.data.split()[1]}"))
        else:
            markup.row(types.InlineKeyboardButton(text='📝Добавить свой отзыв',
                                                  callback_data=f"waiting_for_review"
                                                                f" {self.callback.data.split()[1]}"))
        return markup


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    # первое сообщение и первый ответ
    await bot.send_message(message.from_user.id,
                           f'👋 Привет, {message.from_user.first_name}. Тут ты сможешь найти интересные тебе каналы'
                           f' и узнать мнение наших пользователей о них'
                           f'\n👉 Чтобы узнать больше, введи /help!')


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    # Ответ на команду /help
    await bot.send_message(message.from_user.id,
                           f'Я могу помочь вам узнать мнение других людей о различных telegram каналах'
                           f' и информации внутри них благодаря общему рейтингу'
                           f'\nТакже сдесь вы сможете найти каналы по интересующей вас тематике'
                           f'\n'
                           f'\nВсе, что нужно - это просто отправить мне ссылку на интересуемый telegram канал'
                           f'\n'
                           f'\nВы можете управлять мной, посылая эти команды'
                           f'\n/help - основная информация обо мне'
                           f'\n/top - поможет найти самые высокооцениваемые каналы в выбранной категории')


@dp.message_handler(commands=['top'])
async def process_help_command(message: types.Message):
    # Ответ на команду /top
    list_for_number = []
    markup = types.InlineKeyboardMarkup()
    for j in range(len(tags_db)):  # Цикл создания кнопок
        list_for_number.append(types.InlineKeyboardButton(text=f'{tags[j]}',
                                                          callback_data=f"selection_in_top {j}"))
    for j in range(0, len(list_for_number)):  # Добавление кнопок к сообщению
        if j % 2 == 1:
            markup.row(list_for_number[j - 1], list_for_number[j])
    await bot.send_message(message.from_user.id, 'Выберите, в какой области вы хотите найти лидеров рейтинга',
                           reply_markup=markup)


@dp.message_handler()
async def response_to_link(message: types.Message):
    # обработка отправленной ссылки
    link = LinkRatings(message)
    ready_verification = link.checking_link()  # считывание ответа от функции проверки и выбор ответа для пользователя
    if ready_verification == 'normal':
        link.creation_in_absence_of()
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Дать собственную оценку",
                                                callback_data=f"link_evaluation {message.text}"))
        keyboard.add(types.InlineKeyboardButton(text="Посмотреть отзывы",
                                                callback_data=f"link_reviews {message.text}"))
        await bot.send_message(message.from_user.id, link.creating_response(), reply_markup=keyboard)

    elif ready_verification == 'this is not a channel':
        await bot.send_message(message.from_user.id, '☹️Извините, я не понимаю, что вы мне написали.'
                                                     '\n'
                                                     '\n🤔Скорее всего, то, что ваша ссылка ведёт не на телеграм канал'
                                                     '\n➡️Вы можете использовать команду /help,'
                                                     ' чтобы посмотреть, что я умею')
    else:
        await bot.send_message(message.from_user.id, '☹️Извините, я не понимаю, что вы мне написали.'
                                                     '\n'
                                                     '\n🤔Скорее всего, то, что вы мне отправили, не является ссылкой'
                                                     '\n➡️Вы можете использовать команду /help,'
                                                     ' чтобы посмотреть, что я умею')


@dp.callback_query_handler(Text(startswith='link_reviews'))
async def showing_reviews(callback: types.CallbackQuery):
    # создание промежуточного выбора между отзывом и оценкой
    list_for_number = []
    markup = types.InlineKeyboardMarkup()
    for j in range(0, 11):
        if j != 0:
            list_for_number.append(types.InlineKeyboardButton(text=f'{j}⭐️',
                                                              callback_data=f"general_reviews"
                                                                            f" {callback.data.split()[1]}"
                                                                            f" {j}"))
        else:
            list_for_number.append(types.InlineKeyboardButton(text=f'❔Без оценки',
                                                              callback_data=f"general_reviews"
                                                                            f" {callback.data.split()[1]}"
                                                                            f" {j}"))
    # добавление кнопок, отвечающих за выбор отзыва
    markup.row(list_for_number[1], list_for_number[2], list_for_number[3], list_for_number[4], list_for_number[5])
    markup.row(list_for_number[6], list_for_number[7], list_for_number[8], list_for_number[9], list_for_number[10])
    markup.row(list_for_number[0])
    await bot.send_message(callback.from_user.id, f'👤 Разные люди оставляли свои отзывы '
                                                  f'и они по-разному оценили эту ссылку'
                                                  f'\n'
                                                  f'\nВыбери, какой группы людей ты бы'
                                                  f' хотел посмотреть отзывы', reply_markup=markup)


@dp.callback_query_handler(Text(startswith='general_reviews'))
async def showing_reviews(callback: types.CallbackQuery):
    feedback = []
    for j in cur.execute("SELECT user FROM user_evaluation WHERE estimation = ? AND estimated_link = ?",
                         (callback.data.split()[2], callback.data.split()[1],)).fetchall():
        feedback.append(cur.execute("SELECT * FROM user_reviews WHERE link=?  AND user=?",
                                    (callback.data.split()[1], j[0],)).fetchall()[0])
    # Вывод отзывов пользователю
    print(feedback)
    if feedback:  # определение наличия отзывов на ссылку
        ready_message = ''
        if len(feedback) <= 5:  # ограничение возможного количества выведенных отзывов
            for j in range(len(feedback)):
                ready_message += '*' * int(len(feedback[j][0])) + ': ' + feedback[j][2] + '\n' * 2
        else:
            sp = sample(feedback, 5)
            for j in range(5):
                ready_message += '*' * int(len(sp[j][0])) + ': ' + sp[j][2] + '\n' * 2

        await bot.send_message(callback.from_user.id, ready_message)
    else:
        await bot.send_message(callback.from_user.id, '😦Похоже,'
                                                      ' что люди, так оценившие ссылку, не оставили ни одного отзыва')


@dp.callback_query_handler(Text(startswith='link_evaluation'))
async def evaluation_function(callback: types.CallbackQuery):
    all_about_link = \
        cur.execute("SELECT * FROM opinion_about_link WHERE link=?", (callback.data.split()[1],)).fetchall()[0]
    all_about_opinion = \
        cur.execute("SELECT * FROM user_evaluation WHERE estimated_link=? AND user=?",
                    (callback.data.split()[1], callback.from_user.id,)).fetchall()[0]
    call = CallbackResponses(callback)
    await bot.send_message(callback.from_user.id, call.creating_text_click_response(),
                           reply_markup=call.creating_buttons_click_response(all_about_link, all_about_opinion))


@dp.callback_query_handler(Text(startswith='general_assessment'))
async def general_assessment_link(callback: types.CallbackQuery):
    # сохранение новой оценки пользователя и обновление меню оценки ссылки
    call = CallbackResponses(callback)
    cur.execute(
        '''UPDATE user_evaluation SET estimation = ? WHERE estimated_link=? AND user=?''',
        (int(callback.data.split()[2]), callback.data.split()[1], callback.from_user.id,))
    con.commit()  # изменение оценки пользователя в базе данных
    all_about_link = \
        cur.execute("SELECT * FROM opinion_about_link WHERE link=?", (callback.data.split()[1],)).fetchall()[0]
    all_about_opinion = \
        cur.execute("SELECT * FROM user_evaluation WHERE estimated_link=? AND user=?",
                    (callback.data.split()[1], callback.from_user.id,)).fetchall()[0]
    try:
        # защита в случае, если меню не меняется
        await callback.message.edit_reply_markup(
            reply_markup=call.creating_buttons_click_response(all_about_link, all_about_opinion))
    except MessageNotModified:
        pass


@dp.callback_query_handler(Text(startswith='tags_assessment'))
async def tags_assessment_link(callback: types.CallbackQuery):
    # сохранение новых категорий назначенных пользователем и обновление меню оценки ссылки
    call = CallbackResponses(callback)
    tag_by_account = int(callback.data.split()[2])
    maximum_tags = 0
    all_about_link = \
        cur.execute("SELECT * FROM opinion_about_link WHERE link=?", (callback.data.split()[1],)).fetchall()[0]
    all_about_opinion = \
        cur.execute("SELECT * FROM user_evaluation WHERE estimated_link=? AND user=?",
                    (callback.data.split()[1], callback.from_user.id,)).fetchall()[0]
    for j in range(len(tags)):  # проверка на то, что пользовотель присвоил меньше, чем 3 категории к ссылке
        maximum_tags += all_about_opinion[j + 3]
    if maximum_tags >= 3 and not all_about_opinion[tag_by_account + 3]:
        await bot.send_message(callback.from_user.id, 'Простите, но нельзя добавить к ссылке больше чем 3 тега')
    else:
        cur.execute(f'''UPDATE user_evaluation SET {tags_db[tag_by_account]} = ? 
                    WHERE estimated_link=? AND user=?''',
                    ((all_about_opinion[tag_by_account + 3] + 1) % 2, callback.data.split()[1], callback.from_user.id,))
        cur.execute(f'''UPDATE opinion_about_link SET {tags_db[tag_by_account]} = ? WHERE link=?''',
                    (all_about_link[tag_by_account + 2] - 1 + 2 * ((all_about_opinion[tag_by_account + 3] + 1) % 2),
                     callback.data.split()[1],))
        con.commit()  # сохранение новой категории
        all_about_link = \
            cur.execute("SELECT * FROM opinion_about_link WHERE link=?", (callback.data.split()[1],)).fetchall()[0]
        all_about_opinion = \
            cur.execute("SELECT * FROM user_evaluation WHERE estimated_link=? AND user=?",
                        (callback.data.split()[1], callback.from_user.id,)).fetchall()[0]
        try:
            # страховка на случай, если меню оценки ссылки не нужно обновлять
            await callback.message.edit_reply_markup(
                reply_markup=call.creating_buttons_click_response(all_about_link, all_about_opinion))
        except MessageNotModified:
            pass


@dp.callback_query_handler(Text(startswith='selection_in_top'))
async def category_leaders(callback: types.CallbackQuery):
    # ответ на выбор каналов с лучшей оценкой
    finished_line = f'●Категория: {tags[int(callback.data.split()[1])][1:] + tags[int(callback.data.split()[1])][0]}' \
                    f'\n'
    # нахождение ссылок с нужной котегорией
    ready_made_top = cur.execute(f"SELECT * FROM opinion_about_link WHERE {tags_db[int(callback.data.split()[1])]}"
                                 f" > 0 ORDER BY overall_rating DESC").fetchall()
    if ready_made_top:
        if len(ready_made_top) <= 10:  # ограничение на 10 каналов
            countdown = len(ready_made_top)
        else:
            countdown = 10
        for j in range(countdown):
            rating = cur.execute(f"SELECT AVG(estimation) FROM user_evaluation WHERE estimated_link=?",
                                 (ready_made_top[j][0],)).fetchall()[0][0]
            finished_line += f'\n{j + 1}) {ready_made_top[j][0]}: {rating}⭐️' \
                             f'\n'
    else:
        finished_line += '\n🤷Извинте, в этой категории еще нет каналов.' \
                         '\n' \
                         '\n➡️ Вы можете сами добавить их в меня, просто поделившись со мной ссылкой и добавив тег' \
                         ' соответствующей категории'

    await bot.send_message(callback.from_user.id, finished_line)


class WriteAReview(StatesGroup):
    # оставление отзыва
    waiting_for_a_review = State()


@dp.callback_query_handler(Text(startswith='deleting_review'))
async def function_of_deleting_review(callback: types.CallbackQuery):
    # удаление отзыва
    cur.execute("DELETE FROM user_reviews WHERE link=?  AND user=?",
                (callback.data.split()[1], callback.from_user.id,)).fetchall()
    con.commit()
    await bot.send_message(callback.from_user.id, 'Ваш отзыв удален')


@dp.callback_query_handler(Text(startswith='waiting_for_review'))
async def feedback_waiting_function(callback: types.CallbackQuery):
    global valid_link
    # начало заполнения отзыва
    if cur.execute("SELECT * FROM user_reviews WHERE link=?  AND user=?",
                   (callback.data.split()[1], callback.from_user.id,)).fetchall():
        await bot.send_message(callback.from_user.id, 'У вас уже есть отзыв к этой ссылке')
    else:
        valid_link = callback.data.split()[1]
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton(text='Отменить заполнение отзыва',
                                              callback_data=f"cancellation_of_filling"))
        await WriteAReview.waiting_for_a_review.set()
        await bot.send_message(callback.from_user.id, 'Введите отзыв'
                                                      '\n'
                                                      '\n❗️Правила, которые нельзя нарушать, иначе отзыв не сохранится'
                                                      '\n'
                                                      '\n✅ Только текст'
                                                      '\n✅ Небольше 100 символов'
                                                      '\n'
                                                      '\n❌ Есть мат'
                                                      '\n❌ Есть ссылки на что-либо', reply_markup=markup)


@dp.callback_query_handler(Text(startswith='cancellation_of_filling', ignore_case=True), state='*')
async def cancel_filling(callback: types.CallbackQuery, state: FSMContext):
    # отмена заполнения отзыва
    cancel_state = await state.get_state()
    if cancel_state is None:
        return

    await state.finish()
    await bot.send_message(callback.from_user.id, 'Заполнение отзыва отменено🙂')


class ObsceneSpeechFilter:
    # класс проверки отзыва
    def __init__(self, text):
        self.text = text

    def check(self):
        for key, value in deceptions.items():
            # Проходимся по каждой букве в значении словаря.
            for letter_deceptions in value:
                # Проходимся по каждой букве в отзыве пользователя.
                for letter_text in self.text:
                    # Если символ совпадает с символом в нашем списке.
                    if letter_deceptions == letter_text:
                        # Заменяем эту букву на ключ словаря.
                        self.text = self.text.replace(letter_text, key)

        for word in forbidden_words:
            # Разбиваем слово на части и проходимся по ним.
            for part in range(len(self.text)):
                fragment = self.text[part: part + len(word)]
                # Если отличие этого фрагмента меньше или равно 25% этого слова, то считаем, что они равны.
                if self.calculation_distance(fragment, word) <= len(word) * 0.25:
                    return fragment

    def calculation_distance(self, a, b):
        # Вычисляет расстояние Левенштейна между a и b
        n, m = len(a), len(b)
        if n > m:  # делаем так, чтобы n было меньше m
            a, b = b, a
            n, m = m, n

        current_row = range(n + 1)
        for i in range(1, m + 1):
            previous_row, current_row = current_row, [i] + [0] * n
            for j in range(1, n + 1):
                add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
                if a[j - 1] != b[i - 1]:
                    change += 1
                current_row[j] = min(add, delete, change)

        return current_row[n]

    def search_for_specific_offer(self, word, text):
        # вывод запрешенного слова
        for i in text.split('.'):
            if word in i:
                return i.replace(word, f"___{word}___")


@dp.message_handler(state=WriteAReview.waiting_for_a_review)
async def process_gender(message: types.Message, state: FSMContext):
    # ответна оставление отзыва
    global valid_link
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(text='📝Добавить свой отзыв повторно',
                                          callback_data=f"waiting_for_review"
                                                        f" {valid_link}"))
    if len(message.text) > 100:  # проверка на колчество символов
        await bot.send_message(message.from_user.id, f'😠Количество символов'
                                                     f' в отзыве больше, чем 100 на {len(message.text) - 100}',
                               reply_markup=markup)
    else:
        if valid_link:
            suspicions = ObsceneSpeechFilter(message.text.lower().replace(" ", ""))
            not_like = suspicions.check()
            if not not_like:
                cur.execute("INSERT INTO user_reviews VALUES(?, ?, ?)",
                            (message.from_user.id, valid_link, message.text))
                con.commit()
                valid_link = ''
                await bot.send_message(message.from_user.id, f'Спасибо, что добавили отзыв🫶')
            else:
                a = suspicions.search_for_specific_offer(not_like, message.text)
                if a:
                    await bot.send_message(message.from_user.id, f'😲Похоже, какое-то слово внутри вашего отзыва'
                                                                 f' не понравилось алгоритму проверки на плохие слова'
                                                                 f'\n'
                                                                 f'\nВаш отзыв:'
                                                                 f'\n{a}'
                                                                 f'\n'
                                                                 f'\nВы можете оставить отзыв повторно без этого слова😊',
                                           parse_mode="Markdown", reply_markup=markup)
                else:
                    await bot.send_message(message.from_user.id, f'😲Похоже, какое-то слово внутри вашего отзыва'
                                                                 f' не понравилось алгоритму проверки на плохие слова'
                                                                 f'\n'
                                                                 f'\nНйденое запрещенное слово: {not_like}'
                                                                 f'\n'
                                                                 f'\nВы можете оставить отзыв повторно без этого слова😊',
                                           parse_mode="Markdown", reply_markup=markup)
        else:
            await bot.send_message(message.from_user.id, f'😦Похоже, произошла ошибка при работе с ссылками'
                                                         f'\n'
                                                         f'\n😕Попробуйте оставить отзыв еще раз', reply_markup=markup)
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp)
