import json

from alive_progress import alive_bar
import re

path_to_dictionary = "data/dictionary.txt"
path_to_common_english_words = 'data/top10000words.txt'


def parse_dictionary() -> dict[str, dict[str, list[str]]]:
    with open(path_to_common_english_words, 'r', encoding='utf-8') as file:
        common_words = set(file.read().split('\n'))

    with open(path_to_dictionary, 'r', encoding='utf-8') as file:
        raw_data_string = file.read()

    words_data = raw_data_string.split('\n')
    definition_dictionary = {}

    with alive_bar(len(words_data)) as bar:
        for word in words_data:
            bar()
            is_comment = word.startswith('#') or not word

            if is_comment:
                continue

            german_word, english_definition, part_of_speech, *_ = word.split('\u0009')

            # remove the feminine/masculine/neutral annotation
            german_word = re.sub(" [{][fmn][}]", "", german_word)

            if german_word not in definition_dictionary:
                definition_dictionary[german_word] = {}

            if part_of_speech not in definition_dictionary[german_word]:
                definition_dictionary[german_word][part_of_speech] = []

            # remove "to"
            if part_of_speech == 'verb':
                english_definition = " ".join(english_definition.split()[1:])

            # i.e. laufen    to troll [esp. Br.] [coll.] [walk]	verb
            context = re.findall('\[[^]]+]', english_definition)
            english_definition = re.sub(' \[[^]]+]', '', english_definition)

            definition_dictionary[german_word][part_of_speech].append((english_definition, context))

    for word in definition_dictionary:
        for part_of_speech in definition_dictionary[word]:
            common_translations = list(
                filter(lambda record: record[0] in common_words, definition_dictionary[word][part_of_speech]))

            # filter out obscure english definitions
            if common_translations:
                definition_dictionary[word][part_of_speech] = common_translations

            # join the translation and the context back
            translations = []

            for translation in definition_dictionary[word][part_of_speech]:
                translations.append(translation[0] + " " + " ".join(translation[1]))

            definition_dictionary[word][part_of_speech] = translations

    return definition_dictionary


if __name__ == '__main__':
    def_dict = parse_dictionary()

    with open('data/parsed_dictionary.json', 'w', encoding='utf-8') as file:
        json.dump(def_dict, file)
