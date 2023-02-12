import sqlite3
from contextlib import contextmanager

database = 'db/spaced_repetition.db'


@contextmanager
def get_connection() -> sqlite3.Connection:
    with sqlite3.connect(database) as connection:
        yield connection
        connection.commit()


def setup_database():
    with get_connection() as connection:
        with open('dbsetup.sql') as file:
            script = file.read()

        connection.executescript(script)


def get_schema(table_name) -> list[str]:
    with get_connection() as connection:
        query = f"PRAGMA table_info('{table_name}')"
        result = connection.execute(query).fetchall()

        parsed_res = []

        for col in result:
            # 5th element in the tuple stores weather column is a primary key
            if not col[5]:
                # 1st element stores the name of the column
                parsed_res.append(col[1])

        return parsed_res


def run_insert(table_name: str, *args):

    args = tuple(f"'{arg}'" if isinstance(arg, str) else arg for arg in args)

    schema = get_schema(table_name)

    if len(args) != len(schema):
        raise Exception(f'number of arguments missmatch, columns in db - {len(schema)}, arguments provided - {len(args)}')

    column_names = ", ".join(map(str, schema))
    values = ", ".join(map(str, args))

    query = f"INSERT INTO {table_name} ({column_names}) VALUES({values});"

    with get_connection() as connection:
        connection.execute(query)


def run_select(table_name: str, search_query: dict) -> list[tuple]:
    schema = get_schema(table_name)
    column_names = ", ".join(map(str, schema))

    for key, value in search_query.items():
        if isinstance(value, str):
            search_query[key] = f"'{value}'"

    condition = " AND ".join([f"{key} = {value}" for key, value in search_query.items()])
    query = f"SELECT {column_names} FROM {table_name} WHERE {condition};"

    with get_connection() as connection:
        cursor = connection.execute(query)

        return list(cursor.fetchall())


def run_delete(table_name: str, delete_query: dict):
    for key, value in delete_query.items():
        if isinstance(value, str):
            delete_query[key] = f"'{value}'"

    condition = " AND ".join([f'{key} = {value}' for key, value in delete_query.items()])
    query = f"DELETE FROM {table_name} WHERE {condition}"

    with get_connection() as connection:
        connection.execute(query)

