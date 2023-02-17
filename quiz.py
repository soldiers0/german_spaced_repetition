import random
import re
import time

import ebisu

from word import Word, WordNotFound
from CliUtils import CliBlock
from dbtools import run_insert, run_select, run_delete


class WordNotInQuiz(Exception):
    def __init__(self, word, used_id):
        message = f"{word} not in quiz for user {used_id}"
        super().__init__(message)


class Quiz:
    half_life = 60 * 60 * 24  # a day

    class Table:
        _table_name = 'quiz'

        @classmethod
        def add_new_record(cls, user_id: int, word: Word, ebisu_tuple: tuple[float, float, float]):
            run_insert(cls._table_name, user_id, word.word, word.part_of_speech, *ebisu_tuple, time.time())

        @classmethod
        def get_all_user_words(cls, user_id: int) -> list[tuple[Word, tuple[float, float, float], float]]:
            """
            returns list[word, ebisu, t_elapsed]

            where word is Word object
            ebisu is ebisu tuple
            t_elapsed is time elapsed from last recall, in seconds
            """
            res = run_select(cls._table_name, {
                'user_id': user_id
            })

            parsed_res = []

            for row in res:
                word = row[1]
                part_of_speech = row[2]
                ebisu_tuple = row[3: 6]
                t_elapsed = time.time() - row[6]
                parsed_res.append((Word(word, part_of_speech), ebisu_tuple, t_elapsed))

            return parsed_res

        @classmethod
        def update_word(cls, user_id: int, word: Word, new_ebisu_tuple: tuple[float, float, float]):
            run_delete(cls._table_name, {
                'word': word.word,
                'part_of_speech': word.part_of_speech,
                'user_id': user_id
            })

            run_insert(cls._table_name, user_id, word.word, word.part_of_speech, *new_ebisu_tuple, time.time())

        @classmethod
        def get_word_info(cls, user_id: int, word: Word) -> tuple[Word, tuple[float, float, float], float]:
            """
            returns (word, ebisu, t_elapsed)

            where word is Word object
            ebisu is ebisu tuple
            t_elapsed is time elapsed from last recall, in seconds
            """
            res = run_select(cls._table_name, {
                'user_id': user_id,
                'word': word.word,
                'part_of_speech': word.part_of_speech
            })

            if not res:
                raise WordNotInQuiz(word.word, user_id)

            word = res[0][1]
            part_of_speech = res[0][2]
            ebisu_tuple = res[0][3: 6]
            t_elapsed = time.time() - res[0][6]
            return Word(word, part_of_speech), ebisu_tuple, t_elapsed

        @classmethod
        def check_user_has_word(cls, user_id, word: Word):
            res = run_select(cls._table_name, {
                'user_id': user_id,
                'word': word.word,
                'part_of_speech': word.part_of_speech
            })

            return bool(res)

    def __init__(self, user_id):
        self.user_id = user_id

    def add_new_word(self, word: Word) -> str:
        ebisu_tuple = ebisu.defaultModel(self.half_life)
        self.Table.add_new_record(self.user_id, word, ebisu_tuple)

    def get_lowest_p_word(self) -> Word:
        options = self.Table.get_all_user_words(self.user_id)
        return sorted(options, key=lambda x: ebisu.predictRecall(x[1], x[2]))[0][0]

    def get_word_to_recall(self) -> Word:
        """
        returns a word chosen randomly out of all words in the quiz
        probability of a word coming up is directly tied with the probability of a recall
        """
        options = self.Table.get_all_user_words(self.user_id)

        population = [option[0] for option in options]

        # the weight is squared to give more priority to words that are less likely to be recalled
        weights = [(1 - ebisu.predictRecall(option[1], option[2], exact=1)) ** 2 for option in options]

        return random.choices(population, weights=weights, k=1)[0]

    def update_word(self, word: Word, successes: float, total: float):
        _, old_ebisu, time_elapsed = self.Table.get_word_info(self.user_id, word)
        new_ebisu = ebisu.updateRecall(old_ebisu, successes, total, time_elapsed)
        self.Table.update_word(self.user_id, word, new_ebisu)


class CliQuiz(Quiz):
    def run_add_new_words(self):
        print('to specify part of speech enclose is it [] i.e. [adj]')
        while True:
            with CliBlock() as block:
                try:
                    word = block.input("add new word: ")

                    part_of_speech = re.findall('\[[^]]+]', word)

                    if part_of_speech:
                        part_of_speech = part_of_speech[0][1:-1]
                        word = re.sub(' \[[^]]+]', '', word)
                    else:
                        part_of_speech = None

                    word_obj = Word(word, part_of_speech)
                except WordNotFound:
                    block.input('no such word, press enter button to continue..')
                    continue

                block.print(word_obj.__repr__(), *word_obj.en_definitions, sep='\n')

                if self.Table.check_user_has_word(self.user_id, word_obj):
                    block.print('word already in quiz')
                    block.input('press enter to continue...')
                elif block.input('confirm adding this word Y/N: ').lower() == 'y':
                    self.add_new_word(word_obj)

    def run_quiz(self):
        while True:
            with CliBlock() as word_block:
                lowest_p_word = self.get_lowest_p_word()
                word_block.print(lowest_p_word.word.__repr__())

                total_w = 0
                correct_w = 0
                facts = lowest_p_word.get_facts()

                for fact in facts:
                    with CliBlock(exit_delay=1) as fact_block:
                        if random.random() < fact['p']:
                            fact_block.print(fact['fact'])
                            fact_block.input('press enter to show the answer')
                            fact_block.print(fact['ans'])
                            success = int(fact_block.input('Did you get it right? Y/N ').lower() == 'y')

                            total_w += fact['w']
                            correct_w += success * fact['w']

                self.update_word(lowest_p_word, correct_w / total_w, 1)


if __name__ == '__main__':
    CliQuiz(359230239).run_add_new_words()
