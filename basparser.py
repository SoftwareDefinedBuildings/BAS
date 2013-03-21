from baslexer import BasLexer
import ply.yacc as yacc
from collections import deque

from node import *
import gis
gis.NodeLink.objects.all().delete()
import sdh_demo as sdh

domain = [getattr(sdh, i) for i in sdh.__dict__ if isinstance(getattr(sdh,i), Relational)]

def set_union(set1, set2):
    return set(set1).issubset(set(set2))

class BasParser(object):
    basvars = dict()
    def build(self):
        return yacc.yacc(module=self)

    tokens = BasLexer.tokens

    # STATEMENT
    def p_statement_var(self, p):
        '''statement : VAR EQUALS query'''
        self.basvars[p[1]] = p[3]

    def p_statement_query(self, p):
        '''statement : query'''
        self.lastvalue = p[1]
        p[0] = p[1]

    # SET
    def p_set_query(self, p):
        '''set : LPAREN query RPAREN'''
        p[0] = self.lastvalue = p[2]

    def p_set_lastvalue(self, p):
        '''set : LASTVALUE'''
        p[0] = self.lastvalue

    def p_set_spatial(self, p):
        '''set : SPATIAL'''
        name_lookup = p[1][1:].strip()
        p[0] = self.lastvalue = gis.search(name_lookup)

    def p_set_name(self, p):
        '''set : NAME'''
        name_lookup = p[1][1:].strip()
        print 'Name:', p[0]
        res = []
        for r in domain:
            res.extend(r.search(lambda x: name_lookup in x.get_name()))
        p[0] = self.lastvalue = res

    def p_set_tag(self, p):
        '''set : TAG'''
        tag_lookup = p[1][1:].strip().replace(' ','_')
        res = []
        for r in domain:
            if tag_lookup:
                res.extend(r.search(lambda x: set_union(tag_lookup.split('_'), x.tags)))
            else:
                res.extend(r.search(lambda x: True))

        p[0] = self.lastvalue = res

    def p_set_uuid(self, p):
        '''set : UUID'''
        uuid_lookup = p[1][1:].strip()
        res = []
        print 'start?', p[0]
        for r in domain:
            res.extend(r.search(lambda x: str(x.uid) == uuid_lookup))
        p[0] = self.lastvalue = res

    def p_set_var(self, p):
        '''set : VAR'''
        p[0] = self.basvars.get(p[1],[])

    # QUERY
    def p_query_direction(self, p):
        '''query : query direction set'''
        pass

    def p_query_set(self, p):
        '''query : set'''
        p[0] = self.last_value = p[1]

    # DIRECTION
    def p_direction(self, p):
        '''direction : UPSTREAM
                     | DOWNSTREAM'''
        pass

    def p_error(self, p):
        pass
