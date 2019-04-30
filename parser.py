#!/Library/Frameworks/Python.framework/Versions/3.7/bin/python3
import os
import sys

if len(sys.argv) < 3:
    print('Usage: python3 parser [input.c] [output.ast]\n\tor ./parser [input.c] [output.ast] if permission enabled')
    sys.exit(1)


os.system('python3 lex ' + sys.argv[1] + ' /var/tmp/lex.lex')

class Token:
    def __init__(self, line_num, token_type, value):
        self.line_num = line_num
        self.token_type = token_type
        self.value = value
    def __str__(self):
        return '({},{},"{}")'.format(self.line_num, self.token_type, self.value)

T = []
with open('/var/tmp/lex.lex', 'r') as X:
    lex = X.read()[1:][:-2].split(')\n(')
    for lexeme in lex:
        args = lexeme.split(',')
        if len(args) == 1:
            with open(sys.argv[2],'w') as X:
                pass
            sys.exit(1)
        if args[1] == 'ERROR':
            open(sys.argv[2], 'w')
            sys.exit(1)
        args[2] = args[2][1:][:-1]
        T.append(Token(args[0], args[1], args[2]))

class Leaf:
    def __init__(self, token):
        self.token = token
        if token.token_type == 'ID' or token.token_type == 'NUM':
            self.value = token.token_type
        elif token.value == '' and token.token_type == 'SYM':
            #Assume this is a comma
            self.value = ','
        else:
            self.value = token.value
        self.C = []
    def __str__(self):
        return self.value
    def contains(self, val):
        return self.value == val
    def full(self):
        if self.value == ';;':
            return '[;]'
        if self.value == ';':
            return ''
        x = self.token.value if self.value == 'ID' or self.value == 'NUM' else self.value
        if self.value == '[':
            return '[\[\]]'
        if self.value == ']':
            return ''
            #x = '\['
        return '[{}]'.format(x)
class Node:
    def __init__(self, value, children):
        self.value = value
        self.C = children
    def __str__(self):
        return self.value
    def full(self):
        x = '[{}'.format(self.value)
        for c in self.C:
            x += ' {} '.format(c.full())
        return x + ']'

    def contains(self, val):
        x = '[{}'.format(self.value)
        for c in self.C:
            x += ' {} '.format(c.full())
        print(x)
        return val in x


F = [Leaf(t) for t in T]

def red(i, new):
    global F
    parent = Node(new, [F[i - 1], F[i + 1]])
    F[i - 1 : i + 2] = [parent]

def params(i):
    global F
    j = i + 1
    while True:
        if F[j].value == 'param':
            j += 1
        elif F[j].value == ')':
            break
        else:
            return 1
    parent = Node('params', F[i : j])
    F[i - 1: j + 1] = [parent]

def assign(i):
    global F
    print('Assignment')
    print('{} = {} {}'.format(F[i - 1].value, F[i + 1].value, F[i + 2].value))
    if F[i + 1].value == 'call' and F[i + 2].value not in M + A + R:
        pass
    #elif F[i + 1].value == '=-op':
    #    print('Assign-assign')
    elif F[i - 1].value != 'var' or F[i + 2].value not in [';','}','var']:
        print('Return')
        return 1
    parent = Node('=-op', [F[i - 1], F[i + 1]])
    x = 3 if F[i + 2].value == ';' else 2
    #x = 2 if F[i + 1].value =='call' or 'op' in F[i + 1].value else 3
    F[i - 1 : i + x] = [parent]
    print('Done')

def ret(i):
    global F
    if F[i + 1].value == '}':
        esc()
    if F[i + 1].value == ';':
        parent = Node('return-stmt', [])
        F[i : i + 2] = [parent]
    elif F[i + 1].contains('call'):
        parent = Node('return-stmt', [F[i + 1]])
        F[i : i + 2] = [parent]
    elif F[i + 2].value != ';' and F[i + 1].value != 'call':
        return 1
    else:
        parent = Node('return-stmt', [F[i + 1]])
        x = 3 if F[i + 2].value == ';' else 2
        F[i : i + x] = [parent]


def new_var(i):
    global F
    before = F[i - 1].value
    cur = F[i].value
    after = F[i + 1].value
    #print('New var: {} {} {}'.format(before if i - 1 >= 0 else '', cur, after))
    if after == '(':
        #print('Function call, come back to this')
        return 1
    elif after == 'params':
        good = ['int', 'void', 'fun-declaration', 'var-declaration']
        if F[i + 2].value == 'compound-stmt':
            #print('Function ready')
            parent = Node('fun-declaration', [F[i-1], F[i], F[i+1], F[i+2]])
            F[i - 1 : i + 3] = [parent]
        else:
            return 1
    elif before == 'int':
        if after == ';':
            #print('This is a var-declaration')
            parent = Node('var-declaration', [F[i - 1], F[i]])
            F[i - 1 : i + 2] = [parent]
        elif after == '(':
            #print('Come back to this')
            return 1
        elif after == ',' or after == ')':
            #print('This is a param')
            parent = Node('param', [F[i - 1], F[i]])
            F[i - 1 : i + (2 if after == ',' else 1)] = [parent]
        elif after == '[':
            #print('This could be a few things')
            if F[i + 2].value == ']':
                #print('This is an array param')
                parent = Node('param', [F[i - 1], F[i], F[i + 1], F[i + 2]])
                x = 3 if F[i + 3].value == ')' else 4
                F[i - 1 : i + x] = [parent]
            if F[i + 2].value == 'NUM':
                #print('This is an array dec')
                parent = Node('var-declaration', [F[i - 1], F[i], F[i + 2]])
                F[i - 1 : i + 5] = [parent]
    elif before == 'void':
        #print('Come back to this')
        if after == ';':
            print('This is a bad variable')
            parent = Node('var-declaration', [F[i - 1], F[i]])
            F[i - 1 : i + 2] = [parent]
            return
        return 1
    else:
        if after == '[':
            print('This is an array access')
            while True:
                done = True
                l, r = borders(i + 1)
                if r - l > 2:
                    print('Math!')
                    for x in range(l, r):
                        if F[x].value == 'ID':
                            return 1
                        if F[x].value in M + A + R:
                            gemdas(x)
                            done = False
                            break
                l, r = borders(i + 1)
                if done:
                    break
            print([F[x].value for x in range(l, r + 1)])

            if F[i + 2].value == 'ID':
                return 1

            if F[i + 2].value == 'call' and F[i + 3].value == ';':
                pass
            elif F[i + 3].value != ']':
                esc()

            parent = Node('var', [F[i], F[i + 2]])
            F[i : i + 4] = [parent]
        else:
            #print('This is a var access')
            parent = Node('var', [F[i]])
            F[i] = parent

def compound(i):
    global F
    j = i + 1
    try:
        while True:
            x = F[j].value
            if x == ';' and F[j - 1].value == '{':
                F[j].value = ';;'
            print('In compound: ' + x)
            print([str(f) for f in F])
            if x == '=':
                return 1
            if x in M + A + R:
                return 1
            if x == '{':
                return 1
            if x == 'if' or x == '(' or x == ')' or x == 'while' or x == 'return' or x == 'ID':
                return 1
            if x == '}':
                break
            j += 1
    except Exception as e:
        print([str(f) for f in F])
        print(e)
        esc()
    parent = Node('compound-stmt', F[i + 1 : j])
    print('{} compound-stmt {}'.format(F[i].value, F[j].value))
    F[i : j + 1] = [parent]

statement = ['expression-stmt', 'compound-stmt', 'selection-stmt', 'iteration-stmt', 'return-stmt']
def participle(i): #at ) or else
    x = F[i + 1].value
    y = F[i + 2].value
    return ';' in x, x in statement, ('op' in x or x == 'NUM') and y ==';'


def select(i):
    global F
    condition = F[i + 2]
    if 'op' in condition.value:
        print('Conditional satisfied.  Checking for else...')
        if_else = False
        #if ( op ) stmt else stmt
        #if ( op ) op ; else op ;
        #if ( op ) ;    else ;
        try:
            if F[i + 5].value == '}':
                pass
            elif F[i + 5].value == 'else' or F[i + 6].value == 'else':
                print('else detected')
                if_else = True
        except:
            print([str(f) for f in F])
            sys.exit(1)
        no_op, stmt, two_piece = participle(i + 3)
        if no_op:
            F[i + 4].value = ';;'

        if no_op or stmt:
            print('No operation or with statement...')
            if if_else:
                print('With else.')
                no_op, stmt, two_piece = participle(i + 5)
                if not no_op and not stmt and not two_piece:
                    return 1

                parent = Node('selection-stmt', [condition, F[i + 4], F[i + 6]])
                x = 7 if no_op or stmt else 8
                F[i : i + x] = [parent]
                return
            else:
                print('Without else.')
                parent = Node('selection-stmt', [condition, F[i + 4]])
                F[i : i + 5] = [parent]
                return
        elif two_piece:
            print('Two piece')
            if if_else:
                print('With else.')
                no_op, stmt, two_piece = participle(i + 6)
                if not no_op and not stmt and not two_piece:
                    return 1
                parent = Node('selection-stmt', [condition, F[i + 4], F[i + 7]])
                x = 8 if no_op or stmt else 9
                F[i : i + 9] = [parent]
                return
            else:
                print('Without else.')
                parent = Node('selection-stmt', [condition, F[i + 4]])
                F[i : i + 6] = [parent]
                return

    return 1




def old_select(i):
    global F
    #if ( op ) stmt
    if 'op' in F[i + 2].value:
        print('Conditional satisfied')
        print('if ( {} ) {} {}'.format(F[i + 2].value, F[i + 4].value, F[i + 5].value))
        #DEAL WITH ELSE
        if F[i + 5].value == 'else':
            if ('op' in F[i + 6].value or F[i + 6].value == 'NUM')and F[i + 7].value == ';':
                parent = Node('selection-stmt', [F[i + 2], F[i + 4], F[i + 6]])
        if F[i + 5].value == ';' and F[i + 4].value not in statement:
            print('One liner, assignment or some such')
            if 'op' not in F[i + 4].value and F[i + 4].value != 'NUM':
                return 1
            parent = Node('selection-stmt', [F[i + 2], F[i + 4]])
            F[i : i + 6] = [parent]
            return
    if F[i + 1].value == '(' and 'op' in F[i + 2].value and F[i + 3].value == ')' and F[i + 4].value == ';':
        parent = Node('selection-stmt', [F[i + 2], F[i + 4]])
        F[i + 4].value = ';;'
        F[i : i + 5] = [parent]
    if F[i + 4].value not in statement or 'op' not in F[i + 2].value:
        return 1
    if F[i + 5].value == 'else':
        print('if else')
        if F[i + 6].value not in statement:
            return 1
        parent = Node('selection-stmt', [F[i + 2], F[i + 4], F[i + 6]])
        F[i : i + 7] = [parent]
    else:
        print('if only')
        parent = Node('selection-stmt', [F[i + 2], F[i + 4]])
        F[i : i + 5] = [parent]


def my_iter(i):
    global F
    print('Iterating...')
    if F[i + 1].value == ';':
        print('BAD')
        esc()
    print('while ( {} ) {} {}'.format(F[i + 2].value, F[i + 4].value, F[i + 5].value))
    if 'op' in F[i + 2].value:
        print('Conditional satisfied')
        #while ( op ) ;
        if F[i + 5].value == ';' and F[i + 4].value not in statement:
            if 'op' not in F[i + 4].value and F[i + 4].value != 'NUM':
                return 1
            print('One liner, assignment or some such')
            parent = Node('iteration-stmt', [F[i + 2], F[i + 4]])
            F[i : i + 6] = [parent]
            return
        if F[i + 4].value in statement:
            parent = Node('iteration-stmt', [F[i + 2], F[i + 4]])
            F[i : i + 5] = [parent]
            return
        if F[i + 4].value == ';':
            print('Semicolon')
            parent = Node('iteration-stmt', [F[i + 2], F[i + 4]])
            F[i + 4].value = ';;'
            F[i : i + 5] = [parent]
            return
            #print(F[i + 4].value)
    #Possibly deprecated
    if 'op' in F[i + 2].value and (F[i + 4].value == 'compound-stmt' or F[i + 4].value == ';'):
        parent = Node('iteration-stmt', [F[i + 2], F[i + 4]])
        F[i : i + 5] = [parent]
        return
    return 1

def empty_params(i):
    global F
    parent = Node('params', [])
    F[i - 1 : i + 2] = [parent]

def verify():
    global F
    for f in F:
        if 'declaration' not in f.value:
            return 1
    print('Program ready')
    parent = Node('program', F)
    F = [parent]

R = ['<=', '<', '>', '>=', '==', '!=']
M = ['*', '/']
A = ['+', '-']
def gemdas(i):
    global F
    print([str(f) for f in F])
    l, r = borders(i)
    if gemdas_helper(l, r, M) == 1:
        return 1

    l, r = borders(l)
    if gemdas_helper(l, r, A) == 1:
        return 1

    l, r = borders(l)

    if gemdas_helper(l, r, R) == 1:
        return 1
    l, r = borders(l)

def borders(i, LEFT=[';', '=', '(', ',', '['], RIGHT=[';', ')', ',', ']']):
    #First, find left border
    try:
        left = None
        left_pos = i
        fun = False
        while True:
            if fun and F[left_pos].value == '(':
                fun = False
            elif F[left_pos].value == ')':
                fun = True
            elif F[left_pos].value in LEFT:
                left = F[left_pos].value
                break
            left_pos -= 1
        right = None
        right_pos = i + 1
        while True:
            if fun and F[right_pos].value == ')':
                fun = False
            elif F[right_pos].value == '(':
                fun = True
            elif F[right_pos].value in RIGHT:
                right = F[right_pos].value
                break
            right_pos += 1
        print( [F[x].value for x in range(left_pos, right_pos + 1) ] )
        return (left_pos, right_pos)
    except:
        esc()

def gemdas_helper(left_pos, right_pos, C):
    global F
    while True:
        found = False
        for j in range(left_pos, right_pos + 1):
            x = F[j].value
            print('Gemdas helper: ' + x)
            if x == 'ID':
                new_var(j)
            if x in C:
                print('{} {} {}'.format(F[j - 1].value, F[j].value, F[j + 1].value))
                if F[j + 1].value == '(':
                    gemdas(j + 2)
                    return 1
                parens = False
                if F[j - 2].value == '(' and F[j+2].value == ')' and F[j - 3].value not in ['ID', 'if', 'while']:
                    print('PARENS')
                    parens = True
                if F[j-1].value[0] in R or F[j+1].value[0] in R:
                    esc()
                parent = Node('{}-op'.format(x), [F[j - 1], F[j + 1]])
                y = 2 if parens else 1
                z = 3 if parens else 2
                F[j - y : j + z] = [parent]
                if parens:
                    right_pos -= 4
                else:
                    right_pos -= 2
                ret = j
                found = True
                break
        if not found:
            break


def get_args(begin, end): #(
    print('Getting arguments at {}-{}'.format(str(begin), str(end)))
    global F
    print(F[begin].value)
    print(F[end].value)
    if begin + 1 == end:
        parent = Node('args', [])
        F[begin : end + 1] = [parent]
        return

    i = begin
    cur = i + 1
    args = []
    fun = False
    while True:
        i += 1
        if fun and F[i].value == ')':
            fun = False
        elif F[i].value == 'ID' and F[i + 1].value == '(':
            fun = True
        elif (F[i].value == ',' or F[i].value == ')') and not fun:
            if F[i].value == ',' and F[i + 1].value == ')':
                esc()
            comma = i
            if comma - cur == 1:
                try:
                    print('Test:{}'.format(F[cur].value))
                    assert(F[cur].value not in M + A + R)
                except:
                    esc()
                args.append(F[cur])
            else:
                for i in range(cur, comma):
                    if F[i].value == 'ID' and F[i + 1].value == '(':
                        print('hi')
                        my_call(i)
                        print('Out: {}'.format(F[i].value))
                        args.append(F[i])
                        end -= comma - cur
                        comma = cur + 1
                        break
                else:
                    for i in range(cur, comma):
                        if F[i].value in M + A + R:
                            gemdas(i)
                            args.append(F[cur])
                            end -= comma - cur - 1
                            comma = cur + 1
                            break
            cur = comma + 1
        print('here')
        if i == end:
            print('gone')
            break
    parent = Node('args', args)
    F[begin : end + 1] = [parent]

def esc():
    with open(sys.argv[2], 'w') as X:
        pass
    sys.exit(1)

def my_call(i): #ID
    global F
    l, r = borders(i + 1, LEFT='(', RIGHT=')')
    get_args(l, r)
    if F[i + 2].value == '=':
        print('BAD')
        esc()
    parent = Node('call', [F[i], F[i + 1]])
    print(F[i].full())
    print(F[i + 1].value)
    print(F[i + 2].value)
    x = 3 if F[i + 2].value == ';' else 2
    F[i : i + x] = [parent]

X = ['NUM', 'ID', 'var']
for i in range(len(F)):
    if F[i].value == ',' and F[i+1].value == ')':
        print('Dangling comma')
        esc()
    if F[i].value in X and F[i + 1].value in X:
        print('Missing semicolon')
        esc()
    if F[i].value in X and F[i + 1].value == '}':
        print('Missing semicolon')
        esc()
    if F[i].value == '[' and F[i - 1].value != 'ID':
        print('Array access without variable')
        esc()


ctr = 0
while True:
    done = True
    for i in range(len(F)):
        x = F[i].value
        if x == 'ID':
            if new_var(i) != 1:
                done = False
                break
    ctr += 1
    if ctr == 100:
        esc()
    if done:
        break

while True:
    done = True
    for i in range(len(F)):
        bad = ['int', 'void']
        if F[i].value == 'ID' and F[i + 1].value == '(' and F[i + 2].value not in bad and F[i - 1].value not in bad:
            my_call(i)
            done = False
            break
    if done:
        break

while True:
    done = True
    for i in range(len(F)):
        if F[i - 1].value == '(' and F[i].value == 'NUM' and F[i + 1].value == ')':
            F[i - 1 : i + 2] = [F[i]]
            done = False
            break
    if done:
        break

for i in range(len(F)):
    if F[i].value == 'NUM' and F[i + 1].value == '[':
        print('Bad subscripting')
        esc()

ctr = 0
found = False
while True:
    for i in range(len(F)):
        x = F[i].value
        if x == 'ID':
            if new_var(i) != 1:
                break
        if x in R or x in M or x in A:
            gemdas(i)
            break
        if x == 'param':
            if params(i) != 1:
                break
        if x == '=':
            if assign(i) != 1:
                break
        if x == 'return':
            if ret(i) != 1:
                break
        if x == '{':
            if compound(i) != 1:
                break
        if x == 'if':
            if select(i) != 1:
                break
        if x == 'while':
            if my_iter(i) != 1:
                break
        if x == 'void' and F[i - 1].value == '(' and F[i + 1].value == ')':
            empty_params(i)
            break
        if x == 'var-declaration' or x == 'fun-declaration':
            if verify() != 1:
                found = True
                break
        if x == 'call' and F[i + 1].value == ')' and F[i + 2].value == ';':
            F = F[:i + 1] + F[i + 3:]
            break

    if found:
        break
    ctr += 1
    if ctr == 100:
        break


print('-'*10)
print( [f.full() for f in F] )
#print(F[0].full())

try:
    assert(len(F) == 1)
except:
    esc()

#Semantic analysis
class Symbol:
    def __init__(self, name, t, sz=-1):
        self.t = t
        self.name = name
        self.sz = sz
    def __str__(self):
        if self.t == 'array':
            return '{} {}[{}]'.format(self.t, self.name, self.sz if self.sz > -1 else '')
        else:
            return '{} {}'.format(self.t, self.name)
class Function:
    def __init__(self, name, return_type, params):
        self.name = name
        self.rt = return_type
        self.params = params
        self.scope = [p for p in params]

    def __str__(self):
        return '{} {}('.format(self.rt, self.name) + ', '.join([str(param) for param in self.params]) + ')'

def create_variable(decl_node, scope):
    array = len(decl_node.C) > 2
    name = decl_node.C[1].token.value
    data_type = decl_node.C[0].value
    print('NEW SYM: {}'.format(name))
    assert(name not in ['if', 'while', 'return', 'else', 'int', 'void'])
    assert(not next((var for var in scope if var.name == name), None))
    #assert(name not in scope)
    assert(data_type == 'int')
    if not array:
        scope.append(Symbol(name, 'variable'))
    else:
        size = decl_node.C[2].token.value
        assert(size == '[' or int(size) > 0)
        size = -1 if size == '[' else int(size)
        scope.append(Symbol(name, 'array', sz=size))

global_scope = []
functions = [
    Function('input', 'int', []),
    Function('output', 'void', [Symbol('x', 'int')]),
    Function('println', 'void', [Symbol('x', 'int')])
]
def check_call(call, local_scope):
    fun_name = call.C[0].token.value
    print('Function name:{}'.format(fun_name))
    match = next((var for var in functions if var.name == fun_name), None)
    assert(match)
    print(match)
    assert(len(call.C[1].C) == len(match.params))
    for i in range(len(match.params)):
        possible_var = call.C[1].C[i]
        if possible_var.value == 'call':
            match_fun = next((fun for fun in functions if fun.name == possible_var.C[0].token.value), None)
            assert(match_fun.rt != 'void')
        if possible_var.value == 'var':
            name = possible_var.C[0].token.value
            sym_match = next((var for var in local_scope if var.name == name), None)
            if not sym_match:
                sym_match = next((var for var in global_scope if var.name == name), None)
            if sym_match.t == 'array' and len(possible_var.C) != 2:
                assert(match.params[i].t == 'array')
            else:
                assert(match.params[i].t != 'array')
            if match.params[i].t == 'array':
                assert(sym_match.t == 'array')

def check_return(node):
    this = functions[-1]
    print(len(node.C))
    if this.rt == 'int':
        assert(len(node.C) == 1)
        if node.C[0].value == 'call':
            fun = next((var for var in functions if var.name == node.C[0].C[0].token.value), None)
            assert(fun.rt != 'void')

    else:
        assert(len(node.C) == 0)


def check_compound_statement_order(node):
    print('Check')
    print(node.value)
    for statement in node.C:
        print(statement.value)
    var_declarations_done = False
    for statement in node.C:
        if statement.value != 'var-declaration':
            if not var_declarations_done:
                var_declarations_done = True
        if statement.value == 'var-declaration' and var_declarations_done:
            esc()


def check(node, local_scope):
    if node.value == 'compound-stmt':
        new_scope = []
        check_compound_statement_order(node)
        for statement in node.C:
            if statement.value != 'var-declaration':
                break
            create_variable(statement, new_scope)
        for statement in node.C:
            check(statement, local_scope + new_scope)
    else:
        if node.value == 'params':
            assert(False)
        if node.value in M + A + R:
            assert(len(node.C) == 2)
        if 'op' in node.value:
            node.value = node.value[0:-3]
        if node.value in M + A + R:
            if node.C[0].value == 'call':
                match_fun = next((fun for fun in functions if fun.name == node.C[0].C[0].token.value), None)
                assert(match_fun.rt != 'void')
        if node.value == 'return-stmt':
            check_return(node)
        if node.value == '=':
            if node.C[1].value == 'call':
                match_fun = next((fun for fun in functions if fun.name == node.C[1].C[0].token.value), None)
                assert(match_fun.rt != 'void')
        if node.value == 'call':
            check_call(node, local_scope)
        if node.value == 'var':
            name = node.C[0].token.value
            print('NAME: {}'.format(name))
            assert(not next((var for var in functions if var.name == name), None))
            match_var = next((var for var in local_scope if var.name == name), None)
            if not match_var:
                match_var = next((var for var in global_scope if var.name == name), None)
            print(name)
            assert(match_var)
            assert(match_var.t != 'array' or len(node.C) == 2)

            assert(next((var.name for var in local_scope if var.name == name), None) or
                   next((var.name for var in global_scope if var.name == name), None))
            if len(node.C) == 2:
                x = next((var for var in local_scope if var.name == name), None)
                if not x:
                    x = next((var for var in global_scope if var.name == name), None)
                print(x)

                assert(x.t == 'array')
                if node.C[1].value == 'NUM':
                    i = int(node.C[1].token.value)
                    print(x.sz)
                    if x.sz == -1:
                        assert(i >= 0)
                    else:
                        assert(i >= 0 and i < x.sz)
                    print('bye')
                elif node.C[1].value == 'call':
                    match_call = next((fun for fun in functions if fun.name == node.C[1].value), None)
                    assert(match_call)
                    assert(match_call.rt != 'void')

        for n in node.C:
            check(n, local_scope)
#Main semantic body
try:
    for f in F[0].C:
        if f.value == 'var-declaration':
            create_variable(f, global_scope)
        else:
            params = f.C[2].C
            name = f.C[1].token.value
            data_type = f.C[0].value
            assert(data_type in ['int', 'void'])
            psym = []
            for param in params:
                create_variable(param, psym)
            new_fun = Function(name, data_type, psym)
            assert(not next((fun for fun in functions if fun.name == name), None))
            assert(not next((var for var in global_scope if var.name == name), None))
            global_scope.append(new_fun)
            functions.append(new_fun)
            print('New function name:{}'.format(new_fun.name))
            body = f.C[3]
            if new_fun.rt == 'int':
                assert(body.contains('return-stmt'))
            for statement in body.C:
                if statement.value != 'var-declaration':
                    break
                create_variable(statement, global_scope[-1].scope)
            check_compound_statement_order(body)
            for statement in body.C:
                check(statement, global_scope[-1].scope)
except Exception as e:
    print('BAD')
    print(type(e).__name__)
    with open(sys.argv[2], 'w') as X:
        pass
    sys.exit(1)



print( [str(sym) for sym in global_scope] )

main = global_scope[-1]
try:
    assert(main.name == 'main' and len(main.params) == 0 and main.rt == 'void')
except:
    esc()

with open(sys.argv[2], 'w') as X:
    X.write(F[0].full())
    X.write('\n')
print( [f.full() for f in F])
print('Good')
