import pickle
import re
import typing

from word import Word, WordNotFound, WordQuiz, DefinitionNotFound
from quiz import Quiz
import aiogram

with open('data/token.txt', 'r') as file:
    token = file.read()

with open('data/telegram_whitelist.txt', 'r') as file:
    whitelist = list(map(int, file.read().split('\n')))

bot = aiogram.Bot(token)
buttons_in_a_row = 3


def get_keyboard(answers: typing.Iterable[str], add_back=True) -> aiogram.types.ReplyKeyboardMarkup:
    keyboard = aiogram.types.ReplyKeyboardMarkup()
    answers = list(answers)

    if add_back:
        answers.append('back')

    buttons_count = []
    buttons_to_add = len(answers)

    if buttons_to_add % buttons_in_a_row:
        buttons_count.append(buttons_to_add % buttons_in_a_row)
        buttons_to_add -= buttons_to_add % buttons_in_a_row

    buttons_count.extend([buttons_in_a_row] * (buttons_to_add // buttons_in_a_row))
    ans_iter = iter(answers)

    for row_len in buttons_count:
        keyboard.row()

        for _ in range(row_len):
            keyboard.insert(aiogram.types.KeyboardButton(next(ans_iter)))

    return keyboard


async def report_wrong_input(user_id):
    await bot.send_message(user_id, 'Incorrect input, use keyboard buttons')


class State:
    def __init__(self, user_id):
        self.user_id = user_id
        self.quiz = Quiz(user_id)

    async def enter(self):
        pass

    async def process_msg(self, message: str):
        return self


class AskerState(State):
    """
    a state that just asks user a question and gives multiple choices to answer without any logic
    """
    def __init__(self, user_id: int, message: str, next_steps: dict[str, type[State]]):
        super().__init__(user_id)
        self.message = message
        self.next_steps = next_steps
        self.user_id = user_id

    async def enter(self):
        keyboard = get_keyboard(self.next_steps.keys(), add_back=False)
        await bot.send_message(self.user_id, self.message, reply_markup=keyboard)

    async def process_msg(self, message: str) -> State:
        if message in self.next_steps:
            return self.next_steps[message](self.user_id)

        await report_wrong_input(self.user_id)
        return self


class DefaultState(AskerState):
    """
    Default state that user enters after /start command
    """

    message = "Press add word button to add a new word to your quiz\n\n" \
              "To perform a recall press recall word button"

    next_steps = {}  # to be defined later

    def __init__(self, user_id):
        super().__init__(user_id, self.message, self.next_steps)


def basic_input_handler(commands: list[str] = None):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            self: State = args[0]
            message: str = args[1]
    
            if message == 'back':
                return DefaultState(self.user_id)
    
            if commands and message not in commands:
                await report_wrong_input(self.user_id)
                return self
    
            return await func(*args, **kwargs)
    
        return wrapper
    return decorator


class ConfirmAddNewWordState(State):
    def __init__(self, user_id: int, word: Word):
        super().__init__(user_id)
        self.word = word

    async def enter(self):
        message = '\n'.join([self.word.__repr__()] + self.word.en_definitions + ['confirm adding this word?'])
        answers = ['Yes', 'No']
        await bot.send_message(self.user_id, message, reply_markup=get_keyboard(answers))

    @basic_input_handler(commands=['Yes', 'No'])
    async def process_msg(self, message: str):
        if message == 'Yes':
            self.quiz.add_new_word(self.word)
            return InputNewWordState(self.user_id)
        elif message == 'No':
            return InputNewWordState(self.user_id)


class EnterWordDefinition(State):
    def __init__(self, user_id: int, word: str, part_of_speech: str = None):
        super().__init__(user_id)
        self.word = word
        self.part_of_speech = part_of_speech

    async def enter(self):
        message = "Unable to find a definition in the dictionary\n" \
                  "Enter the translation manually\n" \
                  "Only one definition is accepted"

        if self.part_of_speech is None:
            message += ', specify a part of speech'

        await bot.send_message(self.user_id, message)

    @basic_input_handler()
    async def process_msg(self, message: str):
        if self.part_of_speech is None:
            part_of_speech_ = re.findall('\[[^]]+]', message)

            if part_of_speech_:
                self.part_of_speech = part_of_speech_[0][1:-1]
                message.word = re.sub(' \[[^]]+]', '', message)

        try:
            word_obj = Word(self.word, part_of_speech=self.part_of_speech, definitions=message.split('\n'))
            return ConfirmAddNewWordState(self.user_id, word_obj)
        except WordNotFound:
            message = "Word was not found on wikictionary\n" \
                      "thus there most likely is a typo"

            await bot.send_message(self.user_id, message)
            return InputNewWordState(self.user_id)


class InputNewWordState(State):
    async def enter(self):
        message = "Enter a word you want to add.\n" \
                  "To specify part of speech enclose is it in [] i.e. [adj]"

        await bot.send_message(self.user_id, message, reply_markup=get_keyboard([]))

    @basic_input_handler()
    async def process_msg(self, message: str) -> State:
        word = message
        try:
            part_of_speech = re.findall('\[[^]]+]', word)

            if part_of_speech:
                part_of_speech = part_of_speech[0][1:-1]
                word = re.sub(' \[[^]]+]', '', word)
            else:
                part_of_speech = None

            word_obj = Word(word, part_of_speech)
        except DefinitionNotFound:
            """
            word was not found in the dictionary, but can maybe be found on the wiki
            in this case the english definition should be entered manually
            """
            return EnterWordDefinition(self.user_id, word, part_of_speech=part_of_speech)
        except WordNotFound:
            message = "Word was not found on wikictionary\n" \
                      "thus there most likely is a typo"
            await bot.send_message(self.user_id, message)
            return self

        if self.quiz.Table.check_user_has_word(self.user_id, word_obj):
            message = "Word already in quiz"
            await bot.send_message(self.user_id, message)
            return self

        return ConfirmAddNewWordState(self.user_id, word_obj)


class WordQuizShowAnsState(State):
    def __init__(self, user_id: int, word_quiz_state: State):
        super().__init__(user_id)
        self.word_quiz_state = word_quiz_state

    async def enter(self):
        message = 'Did you recall it right?'
        answers = ['Yes', 'No']

        await bot.send_message(self.user_id, message, reply_markup=get_keyboard(answers))

    @basic_input_handler(commands=['Yes', 'No'])
    async def process_msg(self, message: str):
        self.word_quiz_state.word_quiz.set_ans(message == 'Yes')
        return self.word_quiz_state


class WordQuizState(State):
    def __init__(self, user_id: int, word_quiz: WordQuiz):
        super().__init__(user_id)
        self.word_quiz = word_quiz
        self.is_quiz_over = False

    async def enter(self):
        fact = next(self.word_quiz)

        # quiz is over and fact is a final score
        if type(fact) == tuple:
            correct, total = fact
            message = f'Word recall is over, total score is - {(correct / total) * 100}%\n' \
                      f'press next word to see the start a new quiz\n' \
                      f'press back to go to the main menu'

            options = ['next word']
            keyboard = get_keyboard(options)

            await bot.send_message(self.user_id, message, reply_markup=keyboard)

            self.process_msg = self.exit_message_handler

            self.quiz.update_word(self.word_quiz.word, correct, total)
            return

        message = f'Fact to recall - {fact["fact"]}\n' \
                  f'Press continue when you are ready'

        keyboard = get_keyboard(['continue'])
        await bot.send_message(self.user_id, message, reply_markup=keyboard)

    @basic_input_handler(commands=['next word'])
    async def exit_message_handler(self, message: str) -> State:
        return CreateWordQuizState(self.user_id)

    @basic_input_handler(commands=['continue'])
    async def process_msg(self, message: str) -> State:
        message = f"Answer is\n" \
                  f"{self.word_quiz.last_fact['ans']}"

        await bot.send_message(self.user_id, message)
        return WordQuizShowAnsState(self.user_id, self)


class CreateWordQuizState(State):
    def __init__(self, user_id):
        super().__init__(user_id)
        self.word = self.quiz.get_lowest_p_word()
        self.word_quiz = WordQuiz(self.word)

    async def enter(self):
        message = f"Word is {self.word}, press continue when you are ready to start the word quiz"
        answers = ['continue']

        await bot.send_message(self.user_id, message, reply_markup=get_keyboard(answers))

    @basic_input_handler(commands=['continue'])
    async def process_msg(self, message: str):
        return WordQuizState(self.user_id, self.word_quiz)


DefaultState.next_steps = {
    'new word': InputNewWordState,
    'recall': CreateWordQuizState
}


user_states: dict[int, State] = {}
dp = aiogram.Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start_handler(message: aiogram.types.Message):
    if message.chat.id not in whitelist:
        await bot.send_message(message.chat.id, 'If you want to get access to the bot, contact @soldiersrb\n')
        return

    user_state = DefaultState(message.chat.id)
    await user_state.enter()
    user_states[message.chat.id] = user_state


@dp.message_handler()
async def message_handler(message: aiogram.types.Message):
    if message.chat.id not in whitelist:
        await bot.send_message(message.chat.id, 'If you want to get access to the bot, contact @soldiersrb\n')
        return

    if message.chat.id in user_states:
        user_states[message.chat.id] = await user_states[message.chat.id].process_msg(message.text)
        await user_states[message.chat.id].enter()
        return

    user_state = DefaultState(message.chat.id)
    await user_state.enter()
    user_states[message.chat.id] = user_state

if __name__ == '__main__':
    aiogram.executor.start_polling(dp)
