from baslexer import BasLexer
from basparser import BasParser

lexer = BasLexer().build()
parser = BasParser().build()

def query(string):
    ans = parser.parse(string)
    print ans

if __name__ == '__main__':
    import readline
    while True:
      try:
        q = raw_input("query> ")
      except EOFError:
        print
        break
      if not q:
        continue
      res = query(q)
      print res
