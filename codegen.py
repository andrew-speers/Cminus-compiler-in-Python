import sys
import os

#os.system('python3 parser.py {} /var/tmp/ast.ast'.format(sys.argv[1]))
#print('*\n'*3)

#with open('/var/tmp/ast.ast', 'r') as X:
with open('out/{}.ast'.format(sys.argv[1].split('/')[-1]), 'r') as X:
    ast = ''.join(X.read()[1:].split())
#print(ast)

def done(out):
    with open(sys.argv[2], 'w') as X:
        X.write('\n'.join(out))
        X.write('\n')
    sys.exit(0)

class Node:
    def __init__(self, val):
        self.val = val
        self.children = []
    def __str__(self):
        x = '[{}'.format(self.val)
        for c in self.children:
            x += str(c)
        return x + ']'

L = 0
class Fun:
    op = {
        '+' : 'add',
        '-' : 'sub',
        '*' : 'mul',
        '/' : 'div',
        '<'  : 'blt',
        '>'  : 'bgt',
        '<=' : 'ble',
        '>=' : 'bge',
        '==' : 'beq',
        '!=' : 'bne'
    }
    comp = {
        '<'  : 'blt',
        '>'  : 'bgt',
        '<=' : 'ble',
        '>=' : 'bge',
        '==' : 'beq',
        '!=' : 'bne'
    }
    def __init__(self, name, rt, params, node):
        ##Where node refers to the compound-stmt
        self.name = '_f_{}'.format(name)
        self.rt = rt
        self.params = [x.children[1].val for x in params.children]
        self.p_arr = [len(x.children) == 3 for x in params.children]
        self.node = node

        self.lc = 0
        self.local_count(self.node)
    def __str__(self):
        return self.name
    def local_count(self, node):
        for c in node.children:
            if c.val == 'var-declaration':
                #if len(c.children) == 3:
                #    self.lc += int(c.children[2].val)
                #else:
                self.lc += 1
            self.local_count(c)
    def call(self, call_node, scope=None):
        I = [
            'jal _f_{}'.format(call_node.children[0].val)
        ]
        #arg_ctr = 0
        for a in call_node.children[1].children:
            I = self.arg(a, scope=scope) + [
                'sw $a0, 0($sp)',#.format(arg_ctr),
                'addiu $sp, $sp, -4'
            ] + I
            #arg_ctr += 1
        return I
    def arg(self, arg_node, scope=None):
        if arg_node.val in self.comp:
            return self.bool_expr(arg_node, scope=scope)
        elif arg_node.val in self.op:
            return self.math(arg_node, scope=scope)
        elif arg_node.val == 'var':
            return self.get_var(arg_node, scope=scope)
        elif str.isdigit(arg_node.val):
            return self.get_num(arg_node)
        elif arg_node.val == 'call':
            return self.call(arg_node, scope=scope)
    def bool_expr(self, bnode, scope=None):
        global L
        label = 'bool{}'.format(L)
        end = 'end{}'.format(L)
        L += 1

        return self.math(bnode, goto=label, scope=scope) + [
            'li $a0 0',
            'j {}'.format(end),
            '{}:'.format(label),
            'li $a0 1',
            '{}:'.format(end)
        ]
    def get_var(self, var_node, save=False, scope=None):
        #Coming into this method, $a0 is often already set for this procedure
        #start = ['move $s0 $a0']
        I = [
            'sw $a0 0($sp)',
            'addiu $sp $sp -4'
        ]
        ref = var_node.children[0].val
        print('Ref: {}'.format(ref))
        act = 's' if save else 'l'
        #offset = ['li $a1 0']
        if len(var_node.children) == 2: #Array access
            index = var_node.children[1]
            if str.isdigit(index.val):
                I += self.get_num(index)
            elif index.val == 'var':
                I += self.get_var(index, scope=scope)
            elif index.val in self.op:
                I += self.math(index, scope=scope)

            I += ['move $t1 $a0']
        else:
            I += ['li $t1 0']

        I += [
            #Now we have $t1 as our offset, must multiply it by 4
            'li $t2 4',
            'mul $a1 $t1 $t2',
            #And then bring the original $a0 back
            'addiu $sp $sp 4',
            'lw $a0 0($sp) #Var: {}'.format(ref)
        ]
        if scope:
            ref = self.scoped_var(var_node, scope)
            print('New ref: {}'.format(ref))
        try:
            if self.locs[ref][1]:
                print('Local array')
                I += ['#Local array']
                if len(var_node.children) == 1:
                    print('Array ref')
                    I += ['#Array Reference']
                    return [
                        'la $a0 _{}'.format(ref)
                    ]
                return I + [
                    'la $t0 _{}'.format(ref),
                    'add $a1 $a1 $t0',
                    '{}w $a0 0($a1)'.format(act)
                ]
            print('Default')
            return I + [
                '{}w $a0 {}($fp)'.format(act, self.locs[ref][0])
            ]
        except KeyError:
            print('Not local var')
            I += ['nop #{} not a local variable'.format(ref)]
            if ref in self.params:
                print('Is param')
                I += ['nop #{} is a parameter'.format(ref)]
                param_i = self.params.index(ref)
                if not self.p_arr[param_i]:
                    return I + [
                        '{}w $a0 {}($fp)'.format(act, param_i * 4 + 4)
                    ]
                I += [
                    'lw $t0 {}($fp)'.format(param_i * 4 + 4)
                ]
                print('array manip')
                I += ['nop #Array manip']
                #So now $t0 contains the array address
                if len(var_node.children) == 1:
                    #Always a load
                    return I + [
                        'move $a0 $t0'
                    ]
                #$t0 contains array address
                print('index access')
                I += ['nop #Index access']
                return I + [
                    'add $a1 $a1 $t0',
                    '{}w $a0 0($a1)'.format(act)
                ]

            else:
                I += ['nop #{} is global'.format(ref)]
                print('global')
                if len(var_node.children) == 1 and ref in GA:
                    print('array ref')
                    return [
                        'la $a0 _{} #Global array ref'.format(ref)
                    ]
                return I + [
                    'la $t0 _{}'.format(ref),
                    'add $a1 $a1 $t0',
                    '{}w $a0 0($a1)'.format(act)
                ]
    def get_num(self, num_node):
        return ['li $a0 {}'.format(num_node.val)]
    def math(self, mnode, goto=None, scope=None):
        #cgen(mnode[0] mnode.val mnode[1]):
        cgen1, cgen0 = None,None
        I = [
            '#cgen(mnode[0])',
            'sw $a0, 0($sp)',
            'addiu $sp, $sp, -4',
            '#cgen(mnode[1])',
            'lw $t1, 4($sp)',
            '{} $a0, $t1, $a0'.format(self.op[mnode.val]),
            'addiu $sp, $sp, 4'
        ]
        if goto:
            I = [
                'nop #Comparison of cnode[0]',
                'sw $a0 0($sp)',
                'addiu $sp $sp -4',
                '#to cnode[1]',
                'lw $t1 4($sp)',
                'addiu $sp $sp 4',
                '{} $t1 $a0 {}'.format(self.op[mnode.val], goto)
            ]

        c0, c1 = mnode.children[0], mnode.children[1]
        if str.isdigit(c1.val):
            cgen1 = self.get_num(c1)
        elif c1.val == 'var':
            cgen1 = self.get_var(c1, scope=scope)
        elif c1.val == 'call':
            cgen1 = self.call(c1, scope=scope)
        elif c1.val in self.op:
            cgen1 = self.math(c1, scope=scope)

        if str.isdigit(c0.val):
            cgen0 = self.get_num(c0)
        elif c0.val == 'var':
            cgen0 = self.get_var(c0, scope=scope)
        elif c0.val == 'call':
            cgen0 = self.call(c0, scope=scope)
        elif c0.val in self.op:
            cgen0 = self.math(c0, scope=scope)


        return [I[0]] + cgen0 + I[1:4] + cgen1 + I[4:]
    def assignment(self, node, scope=None):
        if node.children[1].val == 'call':
            return self.call(node.children[1], scope=scope)
        elif str.isdigit(node.children[1].val):
            return self.get_num(node.children[1])
        elif node.children[1].val in self.op:
            return self.math(node.children[1], scope=scope)
        elif node.children[1].val == 'var':
            return self.get_var(node.children[1], scope=scope)
    def ret_stmt(self, node, scope=None):
        if len(node.children) == 0:
            return self.end
        elif str.isdigit(node.children[0].val):
            return self.get_num(node.children[0]) + self.end
        elif node.children[0].val == 'var':
            return self.get_var(node.children[0], scope=scope) + self.end
        elif node.children[0].val == 'call':
            return self.call(node.children[0], scope=scope) + self.end
        elif node.children[0].val in self.op:
            return self.math(node.children[0], scope=scope)
    def declare_var(self, var, var_node):
        is_array = len(var_node.children) == 3
        self.locs[var] = [-1 * (len(self.locs) * 4 + 12), is_array]
        I = []
        if is_array:
            I += [
                '.data',
                '_{}: .space {}'.format(var, int(var_node.children[2].val) * 4),
                '.text'
            ]
        return I
    def scoped_var(self, node, scope):
        want = node.children[0].val
        for var in sorted(scope):
            if want == var[var.count('&'):]:
                print('{} at {}'.format(var, self.locs[var]))
                return var
        return want
    def ctrl(self, node, prefix, scope=None, is_while=False):
        global L
        condition = 'check{}'.format(L)
        label = 'begin{}'.format(L)
        end = 'end{}'.format(L)
        L += 1

        C = []
        if node.children[0].val == '=':
            C = self.assignment(node.children[0], scope=scope) + [
                'beq $a0 $0 {}'.format(end)
            ]  + self.get_var(node.children[0].children[0], scope=scope, save=True) + [
                'j {}'.format(label)
            ]

        else:
            C = self.math(node.children[0], goto=label, scope=scope)

        I = ['{}:'.format(condition)] + C + ['not_{}:'.format(label)]
        if len(node.children) > 2:
            I += ['#Else']
            if node.children[2].val == 'call':
                I += self.call(node.children[2], scope=scope)
            elif node.children[2].val == 'return-stmt':
                I += self.ret_stmt(node.children[2], scope=scope)
            elif node.children[2].val == 'compound-stmt':
                I += self.ret_stmt(node.children[2], scope, prefix + '&')
            elif node.children[2].val == '=':
                I += self.assignment(node.children[2], scope=scope) + self.get_var(node.children[2].children[0], scope=scope, save=True)
        I += ['j {}'.format(end)]

        I += [label + ':']
        body = node.children[1]
        if body.val == 'call':
            I += self.call(body, scope=scope)
        elif body.val == '=':
            I += self.assignment(body, scope=scope) + self.get_var(body.children[0], scope=scope, save=True)
        elif body.val == 'compound-stmt':
            I += self.compound_stmt(body, scope, prefix + '&')
        elif body.val == 'return-stmt':
            I += self.ret_stmt(body, scope=scope)

        if is_while:
            I += ['j {}'.format(condition)]


        return I + [end + ':']
    def resolve_stmt(self, node, scope, prefix, inner=None):
        if node.val == 'var-declaration':
            new_var = prefix + node.children[1].val
            self.declare_var(new_var)
            if inner:
                inner += [new_var]
            else:
                scope += [new_var]
            return []
        elif node.val == 'compound-stmt':
            return self.compound_stmt(node, scope, prefix + '&')
        elif node.val == '=':
            return self.assignment(node, scope=scope) + ['#Assignment'] + self.get_var(node.children[0], save=True, scope=scope)
        elif node.val == 'call':
            return ['#Function call'] + self.call(node, scope=scope)
        elif node.val == 'return-stmt':
            return ['#Return'] + self.ret_stmt(node, scope=scope)
        elif node.val == 'iteration-stmt' or node.val == 'selection-stmt':
            return self.ctrl(node, prefix, scope=scope, is_while=node.val== 'iteration-stmt')

    def compound_stmt(self, node, outer_scope, prefix):
        I = []
        my_scope = []
        for c in node.children:
            if c.val == 'var-declaration':
                new_var = prefix + c.children[1].val
                I += self.declare_var(new_var, c)
                my_scope += [new_var]
            elif c.val == 'compound-stmt':
                I += self.compound_stmt(c, outer_scope + my_scope, prefix + '&')
            elif c.val == '=':
                print(type(self.assignment(c, scope=my_scope + outer_scope)))
                I += self.assignment(c, scope=my_scope + outer_scope) + [
                    '#Assignment'] + self.get_var(c.children[0], save=True,
                                                  scope=my_scope + outer_scope )
            elif c.val == 'call':
                I += ['#Function call'] + self.call(c, scope=my_scope + outer_scope)
            elif c.val == 'return-stmt':
                I += ['#Return'] + self.ret_stmt(c, scope=my_scope + outer_scope)
            elif c.val == 'iteration-stmt' or c.val == 'selection-stmt':
                I += self.ctrl(c, prefix, scope=my_scope + outer_scope,
                               is_while=c.val== 'iteration-stmt')

        return I

    def cgen(self):
        self.locs = {}
        I = [
            '{}:'.format(self.name),
            '#Push return address',
            'sw $ra, 0($sp)',
            'addiu $sp $sp -4',
            '#Push control link',
            'sw $fp, 0($sp)',
            'addiu $sp $sp -4',
            '#Set FP',
            'addiu $fp $sp 8',
            #'addiu $fp $sp {}'.format(len(self.params.children) * 4 + 8),
            '#Push space for local variables',
            'addiu $sp $sp {}'.format(self.lc * -4 -4),
            '#Begin'
        ]

        #M = self.compound_stmt(self.node, [], '')

        self.end = [
            '#Load return address',
            'lw $ra 0($fp)',#.format(len(self.params.children) * 4),
            'move $t0 $fp',
            'lw $fp -4($fp)',#.format(len(self.params.children) * 4 + 4),
            'move $sp $t0',
            'jr $ra',
            '#Exit'
        ]
        M = self.compound_stmt(self.node, [], '')
        return I + M + self.end

class Var:
    def __init__(self, name, t):
        self.name = name
        self.t = t
    def __str__(self):
        return '{} {}'.format(self.name, self.t)

brackets = ['[',']']
def gen():
    i = 0
    for j in range(len(ast)):
        if ast[j] in brackets:
            if ast[i:j]:
                yield ast[i:j]
            yield ast[j]
            i = j + 1

def rec(cur, gen): #We will start at program, not the first bracket
    val = next(gen)
    while val != ']':
        if val not in brackets:
            new = Node(val)
            cur.children.append(new)
        elif val == '[':
            rec(new, gen)
        val = next(gen)

root = Node('root')
rec(root, gen())
program = root.children[0]
print(program)

header = [
    '.text'
]

entry = [
    'main:',
    'jal _f_main',
    'li $v0 10',
    'syscall'
]
output = [
    '_f_output:',
    'lw $a0, 4($sp)',
    'li $v0 1', #Print integer
    'syscall',
    'li $v0 11', #Print character
    'li $a0 0x0a', #Newline
    'syscall',
    'addiu $sp, $sp, 4',
    'li $a0, 0',
    'j $ra'
]
inp = [
    '_f_input:',
    'li $v0 5',
    'syscall',
    'move $a0 $v0',
    'jr $ra'
]


F = []
V = []
GA = []
for c in program.children:
    if c.val == 'fun-declaration':
        args = c.children
        print([str(a) for a in args])
        F.append(Fun(args[1].val, args[0].val, args[2], args[3]))
    if c.val == 'var-declaration':
        offset = 0
        if len(c.children) == 3:
            offset = int(c.children[2].val)
            GA += [c.children[1].val]
        V += [
            '.data',
            '.align 2',
            '_{}: .space {}'.format(c.children[1].val, 4 + offset * 4)
        ]




P = V + ['.text'] + inp + output
for f in F:
    P += f.cgen()
P += entry
done(P)
