CREATE TABLE words (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT,
    part_of_speech TEXT,
    en_definition TEXT
);

CREATE TABLE nouns (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT,
    nom_s TEXT,
    nom_p TEXT,
    gen_s TEXT,
    gen_p TEXT,
    dat_s TEXT,
    dat_p TEXT,
    acc_s TEXT,
    acc_p TEXT,
    article TEXT
);

CREATE TABLE quiz (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    word TEXT,
    part_of_speech TEXT,
    alpha REAL,
    beta REAL,
    t REAL,

);