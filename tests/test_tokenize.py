# -*- coding: utf-8 -*-

import types

import pytest

import sqlparse
from sqlparse import lexer
from sqlparse import sql, tokens as T
from sqlparse.compat import StringIO


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_tokenize_simple(sql_dialect):
    s = 'select * from foo;'
    stream = lexer.tokenize(s, sql_dialect=sql_dialect)
    assert isinstance(stream, types.GeneratorType)
    tokens = list(stream)
    assert len(tokens) == 8
    assert len(tokens[0]) == 2
    assert tokens[0] == (T.Keyword.DML, 'select')
    assert tokens[-1] == (T.Punctuation, ';')


@pytest.mark.parametrize('sql_dialect', [None])
def test_tokenize_backticks(sql_dialect):
    s = '`foo`.`bar`'
    tokens = list(lexer.tokenize(s, sql_dialect=sql_dialect))
    assert len(tokens) == 3
    assert tokens[0] == (T.Name, '`foo`')


@pytest.mark.parametrize('s', ['foo\nbar\n', 'foo\rbar\r',
                               'foo\r\nbar\r\n', 'foo\r\nbar\n'])
def test_tokenize_linebreaks(s):
    # issue1
    tokens = lexer.tokenize(s)
    assert ''.join(str(x[1]) for x in tokens) == s


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_tokenize_inline_keywords(sql_dialect):
    # issue 7
    s = "create created_foo"
    tokens = list(lexer.tokenize(s, sql_dialect=sql_dialect))
    assert len(tokens) == 3
    assert tokens[0][0] == T.Keyword.DDL
    assert tokens[2][0] == T.Name
    assert tokens[2][1] == 'created_foo'
    s = "enddate"
    tokens = list(lexer.tokenize(s, sql_dialect=sql_dialect))
    assert len(tokens) == 1
    assert tokens[0][0] == T.Name
    s = "join_col"
    tokens = list(lexer.tokenize(s, sql_dialect=sql_dialect))
    assert len(tokens) == 1
    assert tokens[0][0] == T.Name
    s = "left join_col"
    tokens = list(lexer.tokenize(s, sql_dialect=sql_dialect))
    assert len(tokens) == 3
    assert tokens[2][0] == T.Name
    assert tokens[2][1] == 'join_col'


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_tokenize_negative_numbers(sql_dialect):
    s = "values(-1)"
    tokens = list(lexer.tokenize(s, sql_dialect=sql_dialect))
    assert len(tokens) == 4
    assert tokens[2][0] == T.Number.Integer
    assert tokens[2][1] == '-1'


def test_token_str():
    token = sql.Token(None, 'FoO')
    assert str(token) == 'FoO'


def test_token_repr():
    token = sql.Token(T.Keyword, 'foo')
    tst = "<Keyword 'foo' at 0x"
    assert repr(token)[:len(tst)] == tst
    token = sql.Token(T.Keyword, '1234567890')
    tst = "<Keyword '123456...' at 0x"
    assert repr(token)[:len(tst)] == tst


def test_token_flatten():
    token = sql.Token(T.Keyword, 'foo')
    gen = token.flatten()
    assert isinstance(gen, types.GeneratorType)
    lgen = list(gen)
    assert lgen == [token]


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_tokenlist_repr(sql_dialect):
    p = sqlparse.parse('foo, bar, baz', sql_dialect=sql_dialect)[0]
    tst = "<IdentifierList 'foo, b...' at 0x"
    assert repr(p.tokens[0])[:len(tst)] == tst


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_single_quotes(sql_dialect):
    p = sqlparse.parse("'test'", sql_dialect=sql_dialect)[0]
    tst = "<Single \"'test'\" at 0x"
    assert repr(p.tokens[0])[:len(tst)] == tst


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_tokenlist_first(sql_dialect):
    p = sqlparse.parse(' select foo', sql_dialect=sql_dialect)[0]
    first = p.token_first()
    assert first.value == 'select'
    assert p.token_first(skip_ws=False).value == ' '
    assert sql.TokenList([]).token_first() is None


def test_tokenlist_token_matching():
    t1 = sql.Token(T.Keyword, 'foo')
    t2 = sql.Token(T.Punctuation, ',')
    x = sql.TokenList([t1, t2])
    assert x.token_matching([lambda t: t.ttype is T.Keyword], 0) == t1
    assert x.token_matching([lambda t: t.ttype is T.Punctuation], 0) == t2
    assert x.token_matching([lambda t: t.ttype is T.Keyword], 1) is None


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_stream_simple(sql_dialect):
    stream = StringIO("SELECT 1; SELECT 2;")

    tokens = lexer.tokenize(stream, sql_dialect=sql_dialect)
    assert len(list(tokens)) == 9

    stream.seek(0)
    tokens = list(lexer.tokenize(stream, sql_dialect=sql_dialect))
    assert len(tokens) == 9

    stream.seek(0)
    tokens = list(lexer.tokenize(stream, sql_dialect=sql_dialect))
    assert len(tokens) == 9


@pytest.mark.parametrize('sql_dialect', [None, 'TransactSQL'])
def test_stream_error(sql_dialect):
    stream = StringIO("FOOBAR{")

    tokens = list(lexer.tokenize(stream, sql_dialect=sql_dialect))
    assert len(tokens) == 2
    assert tokens[1][0] == T.Error


@pytest.mark.parametrize(['expr', 'sql_dialect'], [
    ('JOIN', None),
    ('LEFT JOIN', None),
    ('LEFT OUTER JOIN', None),
    ('FULL OUTER JOIN', None),
    ('NATURAL JOIN', None),
    ('CROSS JOIN', None),
    ('STRAIGHT JOIN', None),
    ('INNER JOIN', None),
    ('LEFT INNER JOIN', None)])
def test_parse_join(expr, sql_dialect):
    p = sqlparse.parse('{0} foo'.format(expr))[0]
    assert len(p.tokens) == 3
    assert p.tokens[0].ttype is T.Keyword


def test_parse_union():  # issue294
    p = sqlparse.parse('UNION ALL')[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].ttype is T.Keyword


@pytest.mark.parametrize(['s', 'sql_dialect'],
                         [('END IF', None),
                          ('END   IF', None),
                          ('END\t\nIF', None),
                          ('END LOOP', None),
                          ('END   LOOP', None),
                          ('END\t\nLOOP', 'TransactSQL'),
                          ('END IF', 'TransactSQL'),
                          ('END   IF', 'TransactSQL'),
                          ('END\t\nIF', 'TransactSQL'),
                          ('END LOOP', 'TransactSQL'),
                          ('END   LOOP', 'TransactSQL'),
                          ('END\t\nLOOP', 'TransactSQL')])
def test_parse_endifloop(s, sql_dialect):
    p = sqlparse.parse(s, sql_dialect=sql_dialect)[0]
    assert len(p.tokens) == 1
    assert p.tokens[0].ttype is T.Keyword


@pytest.mark.parametrize('s', [
    'foo',
    'Foo',
    'FOO',
    'v$name',  # issue291
])
def test_parse_identifiers(s):
    p = sqlparse.parse(s)[0]
    assert len(p.tokens) == 1
    token = p.tokens[0]
    assert str(token) == s
    assert isinstance(token, sql.Identifier)
