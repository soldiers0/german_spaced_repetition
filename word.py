from __future__ import annotations

import itertools
import json
import random

import requests

from bs4 import BeautifulSoup as Soup
from dbtools import run_insert
from dbtools import run_select


class WordNotFound(Exception):
    def __init__(self):
        super().__init__(
            'Word was not found, if its a noun, use upper case first letter, if its a verb use the infinitive')


class DefinitionNotFound(WordNotFound):
    pass


path_to_dictionary = 'data/parsed_dictionary.json'


class Word:
    class Table:
        _table_name = 'words'

        @classmethod
        def get_word_info(cls, word: str, part_of_speech: str) -> None | tuple[str, str, list[str]]:
            res = run_select(cls._table_name, {
                'word': word,
                'part_of_speech': part_of_speech
            })

            if not res:
                return None

            en_definitions = []

            for definition in res:
                en_definitions.append(definition[2])

            return word, part_of_speech, en_definitions

        @classmethod
        def add_word(cls, word: str, part_of_speech: str, en_definitions: list[str]):
            for definition in en_definitions:
                run_insert(cls._table_name, word, part_of_speech, definition)

    with open(path_to_dictionary, 'r', encoding='utf-8') as file:
        de_en_dictionary = json.load(file)

    def __repr__(self):
        return f'{self.word} [{self.part_of_speech}]'

    def __new__(cls, word: str, part_of_speech: str = None, definitions: list[str] = None):
        return_types = {
            'noun': Noun
        }

        if part_of_speech is None:
            part_of_speech = cls._get_most_frequent_part_of_speech(word)

        if part_of_speech in return_types:
            instance = object.__new__(return_types[part_of_speech])
        else:
            instance = object.__new__(Word)

        return instance

    def __init__(self, word: str, part_of_speech: str = None, definitions: list[str] = None):
        if part_of_speech is None:
            part_of_speech = self._get_most_frequent_part_of_speech(word)

        word_info = Word.Table.get_word_info(word, part_of_speech)

        if word_info is None:
            if definitions is None:
                word_info = self._get_word_info(word, part_of_speech)
            else:
                word_info = (word, part_of_speech, definitions)

            Word.Table.add_word(*word_info)

        self.word = word
        self.part_of_speech = part_of_speech
        self.en_definitions = word_info[-1]

    @staticmethod
    def load_wiki_page(word: str) -> Soup:
        url = f'https://de.wiktionary.org/wiki/{word}'
        resp = requests.get(url)

        if resp.status_code == 404:
            raise WordNotFound

        return Soup(resp.text, features="html.parser")

    @classmethod
    def _get_most_frequent_part_of_speech(cls, word: str):
        if word not in cls.de_en_dictionary:
            raise DefinitionNotFound

        return sorted(list(cls.de_en_dictionary[word].items()), key=lambda x: len(list(x)[1]))[-1][0]

    @classmethod
    def _get_word_info(cls, word, part_of_speech):
        if word not in cls.de_en_dictionary or part_of_speech not in cls.de_en_dictionary[word]:
            raise DefinitionNotFound

        en_definitions = cls.de_en_dictionary[word][part_of_speech]

        return word, part_of_speech, en_definitions

    def get_facts(self) -> list[dict]:
        """
        each fact is a dict containing following keys:
        p: float - what is the probability that the fact should be ASKED
        w: float - weight of the fact in the final grading
        ans: str - correct answer
        fact: str - the fact in question to be displayed as task
        """
        return [{
            'p': 1,
            'w': 10,
            'ans': "\n".join(self.en_definitions),
            'fact': "Definition"
        }]


class WordQuiz:
    class AnswerForLastFactNotSet(Exception):
        pass

    def __init__(self, word: Word):
        self.word = word

        self.total_w = 0
        self.correct_w = 0

        facts = word.get_facts()
        self.iter = iter(facts)
        self.last_fact = None
        self.is_ans_set = True

    def set_ans(self, is_correct: bool):
        self.total_w += self.last_fact['w']
        self.correct_w += int(is_correct) * self.last_fact['w']
        self.is_ans_set = True

    def __next__(self) -> dict | tuple[int, int]:
        """
        returns a fact dict

        if no facts are left returns weighed success
        """
        if not self.is_ans_set:
            raise self.AnswerForLastFactNotSet

        while 1:
            next_ = next(self.iter, None)

            if next_ is None or random.random() < next_['p']:
                break

        if next_ is None:
            return self.correct_w, self.total_w

        self.is_ans_set = False
        self.last_fact = next_
        return next_


class Noun(Word):
    """
    args order:
    nom_s, nom_p, gen_s, gen_p, dat_s, dat_p, acc_s, acc_p, article
    """
    part_of_speech = 'noun'

    class Table:
        _table_name = 'nouns'

        @classmethod
        def get_word_info(cls, word) -> tuple | None:
            res = run_select(cls._table_name, {
                'word': word
            })

            if not res:
                return None

            return res[0]

        @classmethod
        def add_word(cls, word, *args):
            run_insert(cls._table_name, word, *args)

    def __init__(self, word, *args, definitions: list[str] = None, **kwargs):
        super().__init__(word, self.part_of_speech, definitions=definitions)

        noun_info = self.Table.get_word_info(word)

        if noun_info is not None:
            # first column is the word itself
            noun_info = noun_info[1:]
        else:
            noun_info = self._get_noun_info(word)
            self.Table.add_word(word, *noun_info)

        self.nom_s, self.nom_p, self.gen_s, self.gen_p, self.dat_s, self.dat_p, self.acc_s, self.acc_p, self.article = \
            noun_info

    @classmethod
    def _get_noun_info(cls, word) -> tuple:
        declension_table = cls.load_wiki_page(word).find('table', {
            'class': 'wikitable float-right inflection-table flexbox hintergrundfarbe2'})
        cases: list[list[Soup]] = [row.findAll('td') for row in declension_table.findAll('tr')[1:]]
        cases_pairs_list = tuple(itertools.chain([cases[i][0].text, cases[i][1].text] for i in range(4)))
        cases_tuple = []

        for pair in cases_pairs_list:
            cases_tuple.extend(pair)

        article = cases_tuple[0].split()[0]
        cases_tuple.append(article)

        return tuple(cases_tuple)

    def _get_weak_declension_cases(self) -> list[str]:
        weak_cases = []
        cases = ['acc_p', 'acc_s', 'dat_s', 'dat_p']

        for case in cases:
            if self.__getattribute__(case).split()[1] != self.__getattribute__(f'nom_{case.split("_")[1]}').split()[1]:
                weak_cases.append(case)

        return weak_cases

    def get_facts(self) -> list[dict]:
        facts = super().get_facts()

        article = {
            'p': 1,
            'w': 5,
            'ans': self.nom_s,
            'fact': 'article'
        }

        facts.append(article)

        plural_form = {
            'p': 0.5,
            'w': 2,
            'ans': self.nom_p,
            'fact': 'plural form'
        }

        for case in self._get_weak_declension_cases():
            code_to_word = {
                'acc': 'accusative',
                'dat': 'dative',
                'p': 'plural',
                's': 'singular'
            }

            weak_case = {
                'p': 0.75,
                'w': 1,
                'ans': self.__getattribute__(case),
                'fact': " ".join(code_to_word[s] for s in case.split('_'))
            }

            facts.append(weak_case)

        facts.append(plural_form)
        return facts
