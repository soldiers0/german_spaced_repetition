# german_spaced_repetition

## General

 A simple interface for spaced repetition of manually added german words. This project was created for fun and learning but I tried (and will continue) to make it atleast somewhat usable in case anyone finds this project valuable for their studies. 

The main idea is that words in the quiz are added manually, rather than chosen from pre-made buckets, like in most solutions I found online. This helped me compliment my studies with traditional textbooks, which don't incorporate many technics to help you remember the vocabulary, unlike, for example Duolingo.

Cli interface and a Telegram bot server are included in the project. *Currently* the bot is hosted [here](t.me/germanspacedrepetitionbot), to use it contact me in [telgram](t.me/soldiersrb). If at the time of you reading this the bot is no longer online you will have to host it yourself.

## Setup

In order for the project to work, you have to download the German-English dictionary from [dict.cc](dict.cc). According to their terms of use, I am not allowed to post the parsed dictionary, because anyone using their data must familiarize themselves with the terms of use. They also have a vocab trainer on their website.

## Code Structure

If for some ungodly reason you will expirience a desire to contribute to this repository, here's a quick overveiw of the code structure: 

### Word

The lowest level abstraction is the `Word` class, it stores the translation of the word and other part-of-speech-specific information.

### Word_Quiz 

Currently unused, but this interface can be used for training part-of-speech-specific knowlege i.e. if the verb is unregular or a nuon has n-declension. I have moved on from this idea because I have found it quite difficult to implement this interface in a telegram bot, with a pleasent user expirience. The initial commit version utilizes the Word_Quiz, but in reality I have found myself just skipping those additional questions. Also, without some additional tinkering, `ebisu` package doesn't allow a *real* value to represent a recall *quality*.

### Quiz

This interface manages the database of words on a per user basis. Also, in `quiz.py` file lies a simple `CliQuiz`, which allows you to add or recall words using a console interface

### TelegramServer

An absolute abomination of a file in which a terribly implemented finite state machine-esque system can be found. Somehow it works, but it **really** needs to be rewritten. My goal was to just get it up in running ASAP for personal use 
