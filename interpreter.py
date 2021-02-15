'''
    expr   : term ((PLUS | MINUS) term)*
    term   : factor ((MUL | DIV) factor)*
    factor : (PLUS | MINUS) factor | INTEGER | LPAREN expr RPAREN
'''
from enum import Enum
from typing import Any

# ==== Lexical Analyzer ====

class TokenType(Enum):
    START   = 0
    INTEGER = 1
    PLUS    = 2
    MINUS   = 3
    MULT    = 4
    DIV     = 5
    SPACE   = 6
    LPAREN  = 7
    RPAREN  = 8
    EOF     = 9


class Token:
    def __init__(self, type_: TokenType, value: Any):
        self.type = type_
        self.value = value
    
    def __repr__(self) -> str:
        return f'Token<{self.type}, {self.value}>'

class Lexer:

    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = -1
        self.curr_char = None
        self.curr_token = Token(TokenType.START, None)
        self.operations = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.MULT,
            '/': TokenType.DIV
        }

    def __iter__(self):
        return self
    
    def __next__(self):
        if self.curr_token.type == TokenType.EOF:
            raise StopIteration
        return self.get_next_token()

    def advance(self, reverse=False) -> None:
        if reverse:
            self.pos -= 1
            if self.pos > 0:
                self.curr_char = self.source[self.pos]
            else:
                self.curr_char = None
                self.curr_char = Token(TokenType.START, None)
        else:
            self.pos += 1
            if self.pos < len(self.source):
                self.curr_char = self.source[self.pos]
            else:
                self.curr_char = None
                self.curr_token = Token(TokenType.EOF, None)
        
    
    def curr_char_is_digit(self) -> bool:
        return self.curr_char and self.curr_char.isdigit()
    
    def curr_char_is_operation(self) -> bool:
        return self.curr_char and self.curr_char in self.operations.keys()

    def curr_char_is_space(self) -> bool:
        return self.curr_char and self.curr_char.isspace()
    
    def curr_char_is_lparen(self) -> bool:
        return self.curr_char and self.curr_char == '('
    
    def curr_char_is_rparen(self) -> bool:
        return self.curr_char and self.curr_char == ')'

    def take_full_integer(self):
        full_number = ''
        while self.curr_char_is_digit():
            curr_char = self.curr_char
            full_number += curr_char
            self.advance()
        self.advance(reverse=True)
        return int(full_number)

    def get_next_token(self) -> Token:
        self.advance()
        if self.curr_token == TokenType.EOF or self.pos >= len(self.source):
            self.curr_token = self.curr_token = Token(TokenType.EOF, None)
        elif self.curr_char_is_digit():
            self.curr_token = Token(TokenType.INTEGER, self.take_full_integer())
        elif self.curr_char_is_operation():
            self.curr_token = Token(self.operations[self.curr_char], self.curr_char)
        elif self.curr_char_is_lparen():
            self.curr_token = Token(TokenType.LPAREN, '(')
        elif self.curr_char_is_rparen():
            self.curr_token = Token(TokenType.RPAREN, ')')
        elif self.curr_char_is_space():
            return self.get_next_token()
        else:
            self.curr_token = Token(TokenType.EOF, None)
        return self.curr_token

# === Parser / Syntax Analyzer ===

class Ast:
    def __init__(self, token: Token) -> None:
        self.token = token

class UnaryOp(Ast):
    def __init__(self, token: Token, expr: Ast) -> None:
        super().__init__(token)
        self.expr = expr

class BinOp(Ast):
    def __init__(self, token: Token, left: Ast, right: Ast) -> None:
        super().__init__(token)
        self.left = left
        self.right = right
    
    def __str__(self) -> str:
        return f'BinOp<{self.left.token.type.name} {self.token.type.name} {self.right.token.type.name}>'


class Num(Ast):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
    
    def __str__(self) -> str:
        return f'Num<{str(self.token.value)}>'

class Parser:
    def __init__(self, lexical_analyzer: Lexer) -> None:
        self.lexer = lexical_analyzer
        self.curr_token = lexical_analyzer.get_next_token()
    
    def raise_exception(self, error_message):
        raise Exception(error_message)
    
    def eat(self, *or_):
        for type_ in or_:
            if self.curr_token.type == type_:
                self.curr_token = self.lexer.get_next_token()
                return
        expected = ' or '.join(map(lambda t: t.name, or_))
        got = self.curr_token.type.name
        self.raise_exception(f'I was expecting for {expected} but got {got}.')

    def factor(self):
        token = self.curr_token
        if token.type == TokenType.INTEGER:
            self.eat(TokenType.INTEGER)
            return Num(token)
        elif token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            ast_node = self.expr()
            self.eat(TokenType.RPAREN)
            return ast_node
        elif token.type in (TokenType.PLUS, TokenType.MINUS):
            self.eat(TokenType.PLUS, TokenType.MINUS)
            return UnaryOp(token, self.factor())
        self.raise_exception('Invalid Factor')
    
    def term(self):
        factor = self.factor()
        while self.curr_token.type in (TokenType.MULT, TokenType.DIV):
            token = self.curr_token
            self.eat(TokenType.MULT, TokenType.DIV)
            factor = BinOp(token, factor, self.factor())
        return factor
            
    def expr(self):
        term = self.term()
        while self.curr_token.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.curr_token
            self.eat(TokenType.PLUS, TokenType.MINUS)
            term = BinOp(op, term, self.term())
        return term
    
    def parse(self):
        return self.expr()


class NodeVisitor:
    def visit(self, node: Ast):
        method_name = 'visit_' + type(node).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        raise Exception(f'visit_{type(node).__name__} or a generic_visit is not implemented')


class Interpreter(NodeVisitor):
    def __init__(self, ast: Ast) -> None:
        self.ast = ast
        self.operations = {
            TokenType.PLUS : lambda x, y: x + y,
            TokenType.MINUS : lambda x, y: x - y,
            TokenType.MULT : lambda x, y: x * y,
            TokenType.DIV : lambda x, y: x // y
        }
    
    def visit_BinOp(self, node: Ast):
        op = self.operations[node.token.type]
        return op(self.visit(node.left), self.visit(node.right))

    def visit_Num(self, node: Ast):
        return node.token.value
    
    def visit_UnaryOp(self, node: Ast):
        if node.token.type == TokenType.MINUS:
            return -self.visit(node.expr)
        else:
            return +self.visit(node.expr)

    def execute(self):
        return self.visit(self.ast)

def main():
    while True:
        source_code = input('pyparser > ')

        if source_code == ':q':
            print('Oui oui')
            break

        lexer = Lexer(source_code)
        parser = Parser(lexer)
        try:
            ast = parser.parse()
        except:
            print('Invalid Input')
            continue
        interpreter = Interpreter()
        print(interpreter.execute())

if __name__ == '__main__':
    main()
