#!/Library/Frameworks/Python.framework/Versions/3.7/bin/python3

import sys
import os.path

if len(sys.argv) != 3 or not os.path.isfile(sys.argv[1]):
    print('Usage: python3 lex [input.c] [output.lex] \n\tor ./lex [input.c] [output.lex] if permission enabled')
    sys.exit(1)

stream = None
with open(sys.argv[1], 'r') as x:
    stream = str(x.read())

def next_char():
    global stream
    if len(stream) == 0:
        return None
    char = stream[0]
    stream = stream[1:]
    return char

def has_next():
    global stream
    return len(stream) != 0

def letter(char):
    return 65 <= ord(char) <= 90 or 97 <= ord(char) <= 122

def digit(char):
    return 48 <= ord(char) <= 57

candidates = ['<', '>', '=', '!', '/']#, '*']
uniques = ['+', '-', ';', ',', '(', ')', '[', ']', '{', '}', '*']

syms = ['+', '-', '*', '/', '<', '<=', '>', '>=', '==', '!=', '=', ';', ',', '(', ')',
        '[', ']', '{', '}', '/*', '*/']
whitespace = ['\t', '\n', ' ']
keywords = ['else', 'if', 'return', 'void', 'while', 'int']
token = ''

#State flags
lexeme_start = False
csym = False #Is a special symbol candidate
cid = False #Is an id candidate
cnum = False #Is a number candidate
ckey = False #Is a keyword candidate
cmmt = False #Is in comment-mode

comment_line_start = -1 #Indicates the line where the comment began

class Lexeme:
    def __init__(self, char, my_type):
        global line
        self.char = char
        self.t = my_type
        self.line = line

    def __str__(self):
        return '(' + str(self.line)  + ',' + self.t + ',"' + self.char + '")'

def parse(char):
    global token, lexeme_start, csym, cid, cnum, ckey, cmmt
    if cmmt:
        if (char == '*' or char == '/')  and token == '':
            token += char
        elif char == '/' and token == '*':
            cmmt = False
        elif char == '*' and token == '/':
            return Lexeme(token+char, 'ERROR')
        else:
            token = ''
        return False

    if not lexeme_start:
        token = ''

        if char in uniques:
            return [Lexeme(char, 'SYM')]
        if char in candidates:
            token += char
            csym = True
            lexeme_start = True
            return False
        if char in whitespace:
            return False
        if letter(char):
            token += char
            lexeme_start = True
            cid = True
            return False
        if digit(char):
            token += char
            lexeme_start = True
            cnum = True
            return False

        return Lexeme(token+char, 'ERROR')
    else:

        if csym:
            if token + char in syms:
                csym = False
                lexeme_start = False
                if token + char == '/*':
                    cmmt = True
                    token = ''
                    return False
                return [Lexeme(token + char, 'SYM')]
            if token in syms and char in whitespace:
                csym = False
                lexeme_start = False
                return [Lexeme(token, 'SYM')]
            if token in syms and letter(char):
                csym = False
                cid = True
                tmp = token
                token = char
                return [Lexeme(tmp, 'SYM')]
            if token in syms and digit(char):
                csym = False
                cnum = True
                tmp = token
                token = char
                return [Lexeme(tmp, 'SYM')]
            if token in syms and char in syms:
                tmp = token
                token = char
                return [Lexeme(tmp, 'SYM')]
            return Lexeme(token+char, 'ERROR')
        if cid:
            if letter(char) or digit(char):
                token += char
                return False
            if char in whitespace:
                lexeme_start = False
                cid = False
                return [Lexeme(token, 'KEY' if token in keywords else 'ID')]
            if char in uniques:
                lexeme_start = False
                cid = False
                return [Lexeme(token, 'KEY' if token in keywords else 'ID'),
                        Lexeme(char, 'SYM')]
            if char in candidates:
                cid = False
                csym = True
                tmp = token
                token = char
                return [Lexeme(tmp, 'KEY' if token in keywords else 'ID')]
            return Lexeme(token+char, 'ERROR')
        if cnum:
            if digit(char):
                token += char
                return False
            if char in whitespace:
                lexeme_start = False
                cnum = False
                return [Lexeme(token, 'NUM')]
            if char in uniques:
                lexeme_start = False
                cnum = False
                return [Lexeme(token, 'NUM'),
                        Lexeme(char, 'SYM')]
            if char in candidates:
                cnum = False
                csym = True
                tmp = token
                token = char
                return [Lexeme(tmp, 'NUM')]
            return Lexeme(token+char, 'ERROR')




line = 1
with open(sys.argv[2], 'w') as lex:
    while(has_next()):
        c = next_char()
        out = parse(c)
        if cmmt and comment_line_start == -1:
            comment_line_start = line
        if not cmmt:
            comment_line_start = -1
        if c == '\n':
            line += 1
        if out:
            if type(out) == Lexeme and out.t == 'ERROR':
                lex.write(str(out) + '\n')
                sys.exit(1)
            [lex.write(str(x) + '\n') for x in out]

    if cmmt:
        lex.write('(' + str(comment_line_start) + ',ERROR,/*)\n')
