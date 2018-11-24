#
# This file is part of pySMT.
#
#   Copyright 2014 Andrea Micheli and Marco Gario
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import re
import copy
import collections
from six.moves import cStringIO
import pyomt.operators as op
from pyomt.walkers import TreeWalker,DagWalker
from pyomt.walkers.generic import handles
from pyomt.utils import quote
from pyomt.environment import get_env
from pyomt.constants import is_pyomt_fraction, is_pyomt_integer
from pyomt.typing import BOOL, REAL, INT, BVType, ArrayType, STRING


'''
#TODO: -> bveq con = in print con daggify
'''


class HRPrinter(TreeWalker):
    """Performs serialization of a formula in a human-readable way.

    E.g., Implies(And(Symbol(x), Symbol(y)), Symbol(z))  ~>   '(x * y) -> z'
    """

    def __init__(self, stream,env=None):
        TreeWalker.__init__(self, env=env)
        self.stream = stream
        self.write = self.stream.write
        self.fv=[]
        self.stack_subf=[]
    

    def printer(self, f,threshold=None):
        """Performs the serialization of 'f'.

        Thresholding can be used to define how deep in the formula to
        go. After reaching the thresholded value, "..." will be
        printed instead. This is mainly used for debugging.
        """
        self.walk(f,threshold=None)
                

    def walk_threshold(self, formula):
        self.write("...")

    def walk_nary(self, formula, ops):
        args = formula.args()
        if ops==" = " and len(args)==2 and "BV" in str(args[0].get_type()) and "BV" in str(args[1].get_type()):
            #self.write("bveq(")
            #yield args[0]
            #self.write(",")
            #yield args[1]
            self.write("(")
            yield args[0]
            self.write("=")
            yield args[1]
        else:
            self.write("(")
            for s in args[:-1]:
                yield s
                self.write(ops)
            yield args[-1]
        self.write(")")

    def walk_quantifier(self, op_symbol, var_sep, sep, formula):
        if len(formula.quantifier_vars()) > 0:
            self.write("(")
            self.write(op_symbol)
            for s in formula.quantifier_vars()[:-1]:
                yield s
                self.write(var_sep)
            yield formula.quantifier_vars()[-1]
            self.write(sep)
            yield formula.arg(0)
            self.write(")")
        else:
            yield formula.arg(0)

    def walk_not(self, formula):
        self.write("(not ")
        yield formula.arg(0)
        self.write(")")

    def walk_symbol(self, formula):
        self.write(quote(formula.symbol_name(), style="'"))

    def walk_function(self, formula):
        yield formula.function_name()
        self.write("(")
        for p in formula.args()[:-1]:
            yield p
            self.write(", ")
        yield formula.args()[-1]
        self.write(")")

    def walk_real_constant(self, formula):
        assert is_pyomt_fraction(formula.constant_value()), \
            "The type was " + str(type(formula.constant_value()))
        # TODO: Remove this once issue 113 in gmpy2 is solved
        v = formula.constant_value()
        n,d = v.numerator, v.denominator
        if formula.constant_value().denominator == 1:
            self.write("%s.0" % n)
        else:
            self.write("%s/%s" % (n, d))

    def walk_int_constant(self, formula):
        assert is_pyomt_integer(formula.constant_value()), \
            "The type was " + str(type(formula.constant_value()))
        self.write(str(formula.constant_value()))

    def walk_bool_constant(self, formula):
        if formula.constant_value():
            self.write("true")
        else:
            self.write("false")

    def walk_bv_constant(self, formula):  #--optimathsat
        # This is the simplest SMT-LIB way of printing the value of a BV
        # self.write("(_ bv%d %d)" % (formula.bv_width(),
        #                             formula.constant_value()))
        #per ora assumo tutti i bv - unsigned
        
        bvsequence=str('{0:0'+str(formula.bv_width())+'b}').format(formula.constant_value())
        bvsequence_comma = re.sub(r'([0-1])(?!$)', r'\1,',bvsequence)
        bvsequence_comma_tf = bvsequence_comma.replace("0","false").replace("1","true")
        self.write("["+bvsequence_comma_tf+"]")

    def walk_algebraic_constant(self, formula):
        self.write(str(formula.constant_value()))

    def walk_bv_extract(self, formula):
        self.write("extractBV(")
        yield formula.arg(0)
        self.write(",%d,%d)" % (formula.bv_extract_start()+1,
                                       formula.bv_extract_end()+1))

    def walk_bv_neg(self, formula):
        self.write("(- ")
        yield formula.arg(0)
        self.write(")")

    def walk_bv_ror(self, formula):
        self.write("(")
        yield formula.arg(0)
        self.write(" ROR ")
        self.write("%d)" % formula.bv_rotation_step())

    def walk_bv_rol(self, formula):
        self.write("(")
        yield formula.arg(0)
        self.write(" ROL ")
        self.write("%d)" % formula.bv_rotation_step())

    def walk_bv_zext(self, formula):
        self.write("(")
        yield formula.arg(0)
        self.write(" ZEXT ")
        self.write("%d)" % formula.bv_extend_step())

    def walk_bv_sext(self, formula):
        self.write("(")
        yield formula.arg(0)
        self.write(" SEXT ")
        self.write("%d)" % formula.bv_extend_step())

    def walk_bv_add(self,formula):
        self.write("sumBV(")
        yield formula.arg(0)
        self.write(",")
        yield formula.arg(1)
        self.write(")")




    
    def walk_bvlt(self,formula):
        self.write("lex_less(")
        yield formula.arg(0)
        self.write(",")
        yield formula.arg(1)
        self.write(")")
    
    def walk_bvle(self,formula):
        self.write("lex_lesseq(")
        yield formula.arg(0)
        self.write(",")
        yield formula.arg(1)
        self.write(")")
    
    def walk_signed_bvlt(self,formula):
        self.write("bvslt(")
        yield formula.arg(0)
        self.write(",")
        yield formula.arg(1)
        self.write(")")
    
    def walk_signed_bvle(self,formula):
        self.write("bvsle(")
        yield formula.arg(0)
        self.write(",")
        yield formula.arg(1)
        self.write(")")
     
    def walk_ite(self, formula): #--optimathsat
        self.write("if ")
        yield formula.arg(0)
        self.write(" then  ")
        yield formula.arg(1)
        self.write("  else  ")
        yield formula.arg(2)
        self.write(" endif ")
    
    def walk_forall(self, formula):
        #return self.walk_quantifier("forall ", ", ", " . ", formula)
        raise NotImplementedErr("The forall operator cannot be translated into Mzn")

    def walk_exists(self, formula):
        #return self.walk_quantifier("exists ", ", ", " . ", formula)
        raise NotImplementedErr("The exists operator cannot be translated into Mzn")

    def walk_toreal(self, formula):
        #self.write("ToReal(")
        yield formula.arg(0)
        #self.write(")")

    def walk_str_constant(self, formula):
        assert (type(formula.constant_value()) == str ), \
            "The type was " + str(type(formula.constant_value()))
        self.write('"%s"' % formula.constant_value())

    def walk_str_length(self,formula):
        self.write("str.len(" )
        self.walk(formula.arg(0))
        self.write(")")

    def walk_str_charat(self,formula, **kwargs):
        self.write("str.at(" )
        self.walk(formula.arg(0))
        self.write(", ")
        self.walk(formula.arg(1))
        self.write(")")

    def walk_str_concat(self,formula, **kwargs):
        self.write("str.++(" )
        for arg in formula.args()[:-1]:
            self.walk(arg)
            self.write(", ")
        self.walk(formula.args()[-1])
        self.write(")")

    def walk_str_contains(self,formula, **kwargs):
        self.write("str.contains(" )
        self.walk(formula.arg(0))
        self.write(", ")
        self.walk(formula.arg(1))
        self.write(")")

    def walk_str_indexof(self,formula, **kwargs):
        self.write("str.indexof(" )
        self.walk(formula.arg(0))
        self.write(", ")
        self.walk(formula.arg(1))
        self.write(", ")
        self.walk(formula.arg(2))
        self.write(")")

    def walk_str_replace(self,formula, **kwargs):
        self.write("str.replace(" )
        self.walk(formula.arg(0))
        self.write(", ")
        self.walk(formula.arg(1))
        self.write(", ")
        self.walk(formula.arg(2))
        self.write(")")

    def walk_str_substr(self,formula, **kwargs):
        self.write("str.substr(" )
        self.walk(formula.arg(0))
        self.write(", ")
        self.walk(formula.arg(1))
        self.write(", ")
        self.walk(formula.arg(2))
        self.write(")")

    def walk_str_prefixof(self,formula, **kwargs):
        self.write("str.prefixof(" )
        self.walk(formula.arg(0))
        self.write(", ")
        self.walk(formula.arg(1))
        self.write(")")

    def walk_str_suffixof(self,formula, **kwargs):
        self.write("str.suffixof(" )
        self.walk(formula.arg(0))
        self.write(", ")
        self.walk(formula.arg(1))
        self.write(")")

    def walk_str_to_int(self,formula, **kwargs):
        self.write("str.to.int(" )
        self.walk(formula.arg(0))
        self.write(")")

    def walk_int_to_str(self,formula, **kwargs):
        self.write("int.to.str(" )
        self.walk(formula.arg(0))
        self.write(")")

    def walk_array_select(self, formula):
        yield formula.arg(0)
        self.write("[")
        yield formula.arg(1)
        self.write("]")

    def walk_array_store(self, formula):
        yield formula.arg(0)
        self.write("[")
        yield formula.arg(1)
        self.write(" := ")
        yield formula.arg(2)
        self.write("]")

    def walk_array_value(self, formula):
        self.write(str(self.env.stc.get_type(formula)))
        self.write("(")
        yield formula.array_value_default()
        self.write(")")
        assign = formula.array_value_assigned_values_map()
        # We sort the array value assigments in lexicographic order
        # for deterministic printing
        for k in sorted(assign, key=str):
            self.write("[")
            yield k
            self.write(" := ")
            yield assign[k]
            self.write("]")

    def walk_bv_tonatural(self, formula):
        self.write("bv2nat(")
        yield formula.arg(0)
        self.write(")")

    def walk_and(self, formula): return self.walk_nary(formula, " /\\ ")
    def walk_or(self, formula): return self.walk_nary(formula, " \/ ")
    def walk_plus(self, formula): return self.walk_nary(formula, " + ")
    def walk_times(self, formula): return self.walk_nary(formula, " * ")
    def walk_div(self, formula): return self.walk_nary(formula, " / ")
    def walk_pow(self, formula): return self.walk_nary(formula, " ^ ")
    def walk_iff(self, formula): return self.walk_nary(formula, " <-> ")
    def walk_implies(self, formula): return self.walk_nary(formula, " -> ")
    def walk_minus(self, formula): return self.walk_nary(formula, " - ")
    def walk_equals(self, formula): return self.walk_nary(formula, " = ") #optimathsat --> bvcomp
    def walk_le(self, formula): return self.walk_nary(formula, " <= ")
    def walk_lt(self, formula): return self.walk_nary(formula, " < ")
    def walk_bv_xor(self, formula): return self.walk_nary(formula, " xor ")
    def walk_bv_concat(self, formula): return self.walk_nary(formula, "::")
    def walk_bv_udiv(self, formula): return self.walk_nary(formula, " u/ ")
    def walk_bv_urem(self, formula): return self.walk_nary(formula, " u% ")
    def walk_bv_sdiv(self, formula): return self.walk_nary(formula, " s/ ")
    def walk_bv_srem(self, formula): return self.walk_nary(formula, " s% ")
    def walk_bv_sle(self, formula): return self.walk_signed_bvle(formula)
    def walk_bv_slt(self, formula): return self.walk_signed_bvlt(formula)
    def walk_bv_ule(self, formula): return self.walk_bvle(formula)
    def walk_bv_ult(self, formula): return self.walk_bvlt(formula)
    def walk_bv_lshl(self, formula): return self.walk_nary(formula, " << ")
    def walk_bv_lshr(self, formula): return self.walk_nary(formula, " >> ")
    def walk_bv_ashr(self, formula): return self.walk_nary(formula, " a>> ")
    def walk_bv_comp(self, formula): return self.walk_nary(formula, " bvcomp ")
    
    #walk_bv_add = walk_plus    
    walk_bv_and = walk_and
    walk_bv_or = walk_or
    walk_bv_not = walk_not
    walk_bv_mul = walk_times
    walk_bv_sub = walk_minus



#EOC HRPrinter


class SmtDagPrinter(DagWalker):
    
    def __init__(self,max_int_bit_size,stream,template="tmp_%d"):
        DagWalker.__init__(self, invalidate_memoization=True)
        self.stream = stream
        self.write = self.stream.write
        self.openings = 0
        self.name_seed = 0
        self.template = template
        self.names = None
        self.mgr = get_env().formula_manager
        self.max_int_bit_size=max_int_bit_size

    def _push_with_children_to_stack(self, formula, **kwargs):
        """Add children to the stack."""

        # Deal with quantifiers
        if formula.is_quantifier():
            # 1. We invoke the relevant function (walk_exists or
            #    walk_forall) to print the formula
            fun = self.functions[formula.node_type()]
            res = fun(formula, args=None, **kwargs)

            # 2. We memoize the result
            key = self._get_key(formula, **kwargs)
            self.memoization[key] = res
        else:
            DagWalker._push_with_children_to_stack(self, formula, **kwargs)

    def printer(self, f):
        self.openings = 0
        self.name_seed = 0
        self.names = set(quote(x.symbol_name()) for x in f.get_free_variables())
        key = self.walk(f)
        self.write(key)
    


    def _new_symbol(self):
        while (self.template % self.name_seed) in self.names:
            self.name_seed += 1
        res = (self.template % self.name_seed)
        self.name_seed += 1
        return res

    def walk_nary(self, formula, args, operator):
        assert formula is not None
        sym = self._new_symbol()
        self.openings += 1
        typeF=str(formula.get_type()).lower().replace("real","float")
        self.write(" let { var %s : %s = ( " % (typeF,sym))
        if operator=="ite":
            self.write(" if ")
            self.write(args[0])
            self.write(" then ")
            self.write(args[1])
            self.write(" else ")
            self.write(args[2])
            self.write(" endif ")
            self.write(" )} in")
        elif len(args)==1 and (operator=="not" or operator=="int2float"):
            self.write(" ")
            self.write(" not (")
            self.write(args[0])
            self.write(")")
            self.write(" )} in \n")
        else:
            self.write(args[0])
            for s in args[1:]:
                self.write(" ")
                self.write(operator)
                self.write(" ")
                self.write(s)
            self.write(" )} in \n")
        return sym

    def walk_and(self, formula, args):
        return self.walk_nary(formula, args, "/\\")

    def walk_or(self, formula, args):
        return self.walk_nary(formula, args, "\/")

    def walk_not(self, formula, args):
        return self.walk_nary(formula, args, "not")

    def walk_implies(self, formula, args):
        return self.walk_nary(formula, args, "->")

    def walk_iff(self, formula, args):
        return self.walk_nary(formula, args, "=")

    def walk_plus(self, formula, args):
        return self.walk_nary(formula, args, "+")

    def walk_minus(self, formula, args):
        return self.walk_nary(formula, args, "-")

    def walk_times(self, formula, args):
        return self.walk_nary(formula, args, "*")

    def walk_equals(self, formula, args):
        return self.walk_nary(formula, args, "=")

    def walk_le(self, formula, args):
        return self.walk_nary(formula, args, "<=")

    def walk_lt(self, formula, args):
        return self.walk_nary(formula, args, "<")

    def walk_ite(self, formula, args):
        return self.walk_nary(formula, args, "ite")

    def walk_toreal(self, formula, args):
        return self.walk_nary(formula, args, "int2float")

    def walk_div(self, formula, args):
        typeF=str(formula.get_type()).lower().replace("real","float")
        if typeF=="float":
            return self.walk_nary(formula, args, "/")
        else:
            return self.walk_nary(formula,args, "div")

    def walk_pow(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        typeF=str(formula.get_type()).lower().replace("real","float")
        self.write("""let { var %s:%s = pow(%s,%s)  
                      } in\n"""%(typeF,sym,args[0],args[1]))
        return sym


    def walk_bv_and(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1 
        typeF=str(formula.get_type()).lower()       
        size=int(re.sub(r"bv{([0-9]+)}",r"\1",typeF))
        self.write(""" let { var int : %s  = sum([pow(2,i)* ((((%s div pow(2,i)) mod 2)) * (((%s div pow(2,i)) mod 2))) | i in 0..%s]);
                       } in\n""" %(sym,args[0],args[1],size-1))
        return sym

    def walk_bv_or(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        typeF=str(formula.get_type()).lower()       
        size=int(re.sub(r"bv{([0-9]+)}",r"\1",typeF))
        self.write(""" let { var int : %s  = sum([pow(2,i)* (((((%s div pow(2,i)) mod 2)) + (((%s div pow(2,i)) mod 2)))>0) | i in 0..%s]);
                       } in\n""" %(sym,args[0],args[1],size-1))
        return sym

    def walk_bv_not(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        typeF=str(formula.get_type()).lower()       
        size=int(re.sub(r"bv{([0-9]+)}",r"\1",typeF))
        self.write(""" let { var int : %s  = sum([pow(2,i)* (1-(%s div pow(2,i)) mod 2) | i in 0..%s]);
                       } in\n""" %(sym,args[0],size-1))
        return sym

    def walk_bv_xor(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        typeF=str(formula.get_type()).lower()       
        size=int(re.sub(r"bv{([0-9]+)}",r"\1",typeF))
        self.write(""" let { var int : %s  = sum([pow(2,i)* (((((%s div pow(2,i)) mod 2)) != (((%s div pow(2,i)) mod 2)))) | i in 0..%s]);
                       } in\n""" %(sym,args[0],args[1],size-1))
        return sym 

    def walk_bv_add(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1       
        size=formula.bv_width()  
        self.write("""let{ var int:%s = (%s+%s) mod %s;
                        } in\n"""%(sym,args[0],args[1],pow(2,size)))
        return sym

    def walk_bv_sub(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1       
        size=formula.bv_width()   
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                            var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                            var int:%s_ris = (%s_args1 - %s_args2) mod %s;
                            var int:%s = if %s_ris < 0 then %s_ris+%s else %s_ris endif;
                       } in\n""" %(sym,args[0],str(pow(2,size-1)),args[0],pow(2,size),args[0],
                                  sym,args[1],str(pow(2,size-1)),args[1],pow(2,size),args[1],
                                  sym,sym,sym,str(pow(2,size)),
                                  sym,sym,sym,str(pow(2,size)),sym))
        return sym

    def walk_bv_neg(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1   
        size=formula.bv_width()   
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                            var int:%s_ris = (0 - %s_args1);
                            var int:%s = if %s_ris < 0 then %s_ris+%s else %s_ris endif;
                        } in\n""" %(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,sym,
                                   sym,sym,sym,str(pow(2,size)),sym))
        return sym


    def walk_bv_mul(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        typeF=int(str(formula.get_type()).lower())       
        size=re.sub(r"bv{([0-9]+)}",r"\1",typeF)    
        self.write(""" let { var int:%s = (%s*%s) mod %s
                        } in\n"""%(sym,args[0],args[1],str(pow(2,size))))
        return sym

            

    def walk_bv_udiv(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1     
        self.write(""" let { var int:%s = (%s div %s)  
                       } in\n"""%(sym,args[0],args[1]))
        return sym

    def walk_bv_urem(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1  
        self.write(""" let { var int:%s = (%s mod %s)  
                        } in\n"""%(sym,args[0],args[1]))
        return sym


    def walk_bv_lshl(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        typeF=str(formula.get_type()).lower()       
        size=re.sub(r"bv{([0-9]+)}",r"\1",typeF)    
        self.write(""" let { var int:%s = (%s*pow(2,%s)) mod %s;
                        } in\n"""%(sym,args[0],args[1],str(pow(2,size))))
        return sym


    def walk_bv_lshr(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1        
        self.write(""" let { var int:%s = (%s div pow(2,%s))
                        } in\n"""%(sym,args[0],args[1]))
        return sym

    def walk_bv_ult(self, formula, args):    #depend on the encoding
        sym = self._new_symbol()
        self.openings += 1
        self.write(""" let { var bool:%s = (%s<%s) 
                        } in\n"""%(sym,args[0],args[1]))
        return sym

    def walk_bv_ule(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        self.write(""" let { var bool:%s = (%s<=%s)
                       } in\n"""%(sym,args[0],args[1]))
        return sym

    def walk_bv_slt(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        size=int(formula.args()[0].bv_width())  
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                             var bool:%s = (%s_args1 < %s_args2)  
                        } in  """%(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,args[1],str(pow(2,size-1)),args[1],str(pow(2,size)),args[1],
                                   sym,sym,sym))
        return sym

    def walk_bv_sle(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        size=int(formula.args()[0].bv_width())  
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                             var bool:%s = (%s_args1 <= %s_args2)  
                        } in  """%(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,args[1],str(pow(2,size-1)),args[1],str(pow(2,size)),args[1],
                                   sym,sym,sym))
        return sym

    def walk_bv_concat(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1
        size_s1=formula.args()[0].bv_width()
        size_s2=formula.args()[1].bv_width()
        self.write(""" let { var int: %s = %s + sum([pow(2,i+%s)*(((%s div pow(2,i)) mod 2)) | i in 0..%s]);
                            } in\n"""%(sym,args[1],size_s2,args[0],size_s1-1))
        return sym

    def walk_bv_comp(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1   
        self.write(""" let { var int : %s  = if %s=%s then 1 else 0 endif;
                        } in\n""" %(sym,args[0],args[1]))
        return sym


    def walk_bv_ashr(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1    
        size=formula.bv_width() 
        self.write(""" let {  var int:%s_args1 = if %s>=%s then %s-%s+%s else %s endif;
                              var int:%s_ris =  %s_args1 div pow(2,%s);
                              var int:%s = if %s<%s  then %s_ris else sum([pow(2,i)*(((%s_ris+%s) div pow(2,i)) mod 2)|i in 0..%s]) endif;
                            } in\n"""%(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),str(pow(2,self.max_int_bit_size-1)),args[0], 
                                      sym,sym,args[1],
                                      sym,args[0],str(pow(2,size-1)),sym,sym,str(pow(2,self.max_int_bit_size-3)+pow(2,self.max_int_bit_size-2)+pow(2,self.max_int_bit_size-1)+pow(2,size)),size-1))
        return sym


    def walk_bv_sdiv(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1       
        size=formula.bv_width()   
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_ris = (%s_args1 div %s_args2);  
                             var int:%s = if %s_ris < 0 then %s_ris+%s else %s_ris endif;
                        } in\n""" %(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,args[1],str(pow(2,size-1)),args[1],str(pow(2,size)),args[1],
                                   sym,sym,sym,
                                   sym,sym,sym,str(pow(2,size)),sym))
        return sym

    def walk_bv_srem(self, formula, args):
        sym = self._new_symbol()
        self.openings += 1       
        size=formula.bv_width()  #(sign follows dividend)
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_ris = (%s_args1 mod %s_args2);
                             var int:%s = if %s_ris < 0 then %s_ris+%s else %s_ris endif;
                        } in\n""" %(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,args[1],str(pow(2,size-1)),args[1],str(pow(2,size)),args[1],
                                   sym,sym,sym,
                                   sym,sym,sym,str(pow(2,size)),sym))
        return sym


    def walk_bv_tonatural(self, formula, args):
        # Kind of useless
        #return self.walk_nary(formula, args, "bv2nat")
        sym = self._new_symbol()
        self.openings += 1
        self.write(""" let { var int:%s = %s;  
                        } in\n"""%(sym,args[0]))
        return sym

    def walk_array_select(self, formula, args):
        return self.walk_nary(formula, args, "select")

    def walk_array_store(self, formula, args):
        return self.walk_nary(formula, args, "store")

    def walk_symbol(self, formula, **kwargs):
        return quote(formula.symbol_name())

    def walk_function(self, formula, args, **kwargs):
        return self.walk_nary(formula, args, formula.function_name())

    def walk_int_constant(self, formula, **kwargs):
        #print "INT CONSTANTANT ",formula.constant_value()
        if formula.constant_value() < 0:
            return "(- " + str(-formula.constant_value()) + ")"
        else:
            return str(formula.constant_value())

    def walk_real_constant(self, formula, **kwargs):
        #print "REAL CONSTANTANT ",formula.constant_value()
        #print "SIMPLY ",formula.constant_value.
        if formula.constant_value() < 0:
            template = "(- %s)"
        else:
            template = "%s"

        (n,d) = abs(formula.constant_value().numerator), \
                    formula.constant_value().denominator
        if d != 1:
            return template % ( "(" + str(n) + " / " + str(d) + ")" )
        else:
            return template % (str(n) + ".0")

    def walk_bv_constant(self, formula, **kwargs):
        return str(formula.constant_value())
        #return "#b" + res


    def walk_bool_constant(self, formula, **kwargs):
        if formula.constant_value():
            return "true"
        else:
            return "false"

    def walk_str_constant(self, formula, **kwargs):
        return '"' + formula.constant_value() + '"'

    def walk_forall(self, formula, args, **kwargs):
        #return self._walk_quantifier("forall", formula, args)
        raise NotImplementedErr("The forall operator cannot be translated into Mzn")

    def walk_exists(self, formula, args, **kwargs):
        #return self._walk_quantifier("exists", formula, args)
        raise NotImplementedErr("The exists operator cannot be translated into Mzn")

    def _walk_quantifier(self, operator, formula, args):
        '''
        assert args is None
        assert len(formula.quantifier_vars()) > 0
        sym = self._new_symbol()
        self.openings += 1

        self.write("(let ((%s (%s (" % (sym, operator))

        for s in formula.quantifier_vars():
            self.write("(")
            self.write(quote(s.symbol_name()))
            self.write(" %s)" % s.symbol_type().as_smtlib(False))
        self.write(") ")

        subprinter = SmtDagPrinter(self.stream,0,0) #Da rivedere
        subprinter.printer(formula.arg(0))

        self.write(")))")
        return sym
        '''
        raise NotImplementedErr("The quantifier cannot be translated into Mzn")

    def walk_bv_extract(self, formula, args, **kwargs):
        assert formula is not None
        sym = self._new_symbol()
        self.openings += 1
        start=int(formula.bv_extract_start())
        end=int(formula.bv_extract_end())
        if start != end:
            self.write(""" let { var int : %s_s1 = %s div %s;
                                 var int : %s = sum([pow(2,i)*(((%s_s1 div pow(2,i)) mod 2)) | i in 0..%s])
                            } in\n"""%(sym,args[0],str(pow(2,start)),sym,sym,str(end-start)))
                                

        else:
            self.write(""" let { var int : %s =  (%s div pow(2,%s)) mod 2;
                            } in\n""" %(sym,args[0],start))
        return sym

    @handles(op.BV_SEXT, op.BV_ZEXT)
    def walk_bv_extend(self, formula, args, **kwargs):
        #pylint: disable=unused-argument
        sym = self._new_symbol()
        self.openings += 1
        if formula.is_bv_zext():
            self.write(""" let { var int:%s = %s;  
                          } in\n"""%(sym,args[0]))
        else:
            assert formula.is_bv_sext() 
            self.write(""" let { var int:%s = %s+sum([pow(2,i) | i in %s..%s ]);  
                           } in\n"""%(sym,args[0],formula.args()[0].bv_width(),formula.bv_width()-1))
        return sym

    @handles(op.BV_ROR, op.BV_ROL)
    def walk_bv_rotate(self, formula, args, **kwargs):
        #pylint: disable=unused-argument
        sym = self._new_symbol()
        self.openings += 1
        size=formula.bv_width()
        rotate=formula.bv_rotation_step()%size
        if formula.is_bv_ror():
            self.write(""" let { var int:%s = (%s div %s + ((%s * %s) mod %s)) mod %s;
                            } in\n"""%(sym,args[0],str(pow(2,rotate)),args[0],str(pow(2,size-rotate)),str(pow(2,size)),str(pow(2,size))))
        else:
            self.write(""" let { var int:%s = (%s div %s) + ((%s * %s mod %s)) mod %s; 
                           } in\n"""%(sym,args[0],str(pow(2,size-rotate)),args[0],str(pow(2,rotate)),str(pow(2,size)),str(pow(2,size))))
        
        return sym

    def walk_str_length(self, formula, args, **kwargs):
        #return "(str.len %s)" % args[0])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_charat(self,formula, args,**kwargs):
        #return "( str.at %s %s )" % (args[0], args[1])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_concat(self, formula, args, **kwargs):
        '''
        sym = self._new_symbol()
        self.openings += 1
        self.write("(let ((%s (%s" % (sym, "str.++ " ))
        for s in args:
            self.write(" ")
            self.write(s)
        self.write("))) ")
        return sym
        '''
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_contains(self,formula, args, **kwargs):
        #return "( str.contains %s %s)" % (args[0], args[1])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_indexof(self,formula, args, **kwargs):
        #return "( str.indexof %s %s %s )" % (args[0], args[1], args[2])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_replace(self,formula, args, **kwargs):
        #return "( str.replace %s %s %s )" % (args[0], args[1], args[2])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_substr(self,formula, args,**kwargs):
        #return "( str.substr %s %s %s)" % (args[0], args[1], args[2])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_prefixof(self,formula, args,**kwargs):
        #return "( str.prefixof %s %s )" % (args[0], args[1])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_suffixof(self,formula, args, **kwargs):
        #return "( str.suffixof %s %s )" % (args[0], args[1])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_to_int(self,formula, args, **kwargs):
        #return "( str.to.int %s )" % args[0]
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_int_to_str(self,formula, args, **kwargs):
        #return "( int.to.str %s )" % args[0]
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_array_value(self, formula, args, **kwargs):
        raise NotImplementedErr("Operation that cannot be translated into MzN")

class DagWalkerFathers(DagWalker):
    def __init__(self,max_int_bit_size,stream,dict_fathers,template="tmp_%d",boolean_invalidate=True):
        DagWalker.__init__(self, invalidate_memoization=boolean_invalidate)
        self.stream = stream
        self.write = self.stream.write
        self.openings = 0
        self.name_seed = 0
        self.memoization = dict_fathers
        self.template = template
        self.names = None
        self.mgr = get_env().formula_manager
        self.max_int_bit_size=max_int_bit_size
        #print "MEMO",self.memoization

    def _push_with_children_to_stack(self, formula, **kwargs):
        """Add children to the stack."""

        # Deal with quantifiers
        if formula.is_quantifier():
            # 1. We invoke the relevant function (walk_exists or
            #    walk_forall) to print the formula
            fun = self.functions[formula.node_type()]
            res = fun(formula, args=None, **kwargs)

            # 2. We memoize the result
            key = self._get_key(formula, **kwargs)
            self.memoization[key] = res
        else:
            DagWalker._push_with_children_to_stack(self, formula, **kwargs)

    def printer(self, f):
        self.openings = 0
        self.name_seed = 0
        self.names = set(quote(x.symbol_name()) for x in f.get_free_variables())
        #print "formula",f,"con mem",self.memoization,"buffer",self.stream.getvalue()
        key = self.walk(f)
        self.write(key)
    
    def _new_symbol_bv(self,bv_template):
        while (bv_template % self.name_seed) in self.names:
            self.name_seed += 1
        res = (bv_template % self.name_seed)
        self.name_seed += 1
        return res
    

    def walk_nary(self, formula, args, operator):
        assert formula is not None
        str_out = ""
        self.openings += 1
        if operator=="ite":
            str_out = str_out + " if "
            str_out=str_out+args[0]
            str_out = str_out + " then " 
            str_out=str_out+args[1]
            str_out = str_out + " else "
            str_out=str_out+args[2]
            str_out = str_out + " endif "
        elif len(args)==1 and (operator=="not" or operator=="int2float"):
            str_out = str_out + " "
            str_out = str_out + " not ("
            str_out=str_out+args[0]
            str_out = str_out + ")"
        else:
            str_out = str_out + "("
            str_out=str_out+args[0]
            for s in args[1:]:
                str_out = str_out + " "
                str_out=str_out+operator
                str_out = str_out + " "
                str_out=str_out+s
            str_out = str_out + ")"
        return str_out

    def walk_and(self, formula, args):
        return self.walk_nary(formula, args, "/\\")

    def walk_or(self, formula, args):
        return self.walk_nary(formula, args, "\/")

    def walk_not(self, formula, args):
        return self.walk_nary(formula, args, "not")

    def walk_implies(self, formula, args):
        return self.walk_nary(formula, args, "->")

    def walk_iff(self, formula, args):
        return self.walk_nary(formula, args, "=")

    def walk_plus(self, formula, args):
        return self.walk_nary(formula, args, "+")

    def walk_minus(self, formula, args):
        return self.walk_nary(formula, args, "-")

    def walk_times(self, formula, args):
        return self.walk_nary(formula, args, "*")

    def walk_equals(self, formula, args):
        return self.walk_nary(formula, args, "=")

    def walk_le(self, formula, args):
        return self.walk_nary(formula, args, "<=")

    def walk_lt(self, formula, args):
        return self.walk_nary(formula, args, "<")

    def walk_ite(self, formula, args):
        return self.walk_nary(formula, args, "ite")

    def walk_toreal(self, formula, args):
        return self.walk_nary(formula, args, "int2float")

    def walk_div(self, formula, args):
        typeF=str(formula.get_type()).lower().replace("real","float")
        if typeF=="float":
            return self.walk_nary(formula, args, "/")
        else:
            return self.walk_nary(formula,args, "div")

    def walk_pow(self, formula, args):
        return """pow(%s,%s)"""%(args[0],args[1])


    def walk_bv_and(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1 
        typeF=str(formula.get_type()).lower()       
        size=int(re.sub(r"bv{([0-9]+)}",r"\1",typeF))
        self.write(""" let { var int : %s  = sum([pow(2,i)* ((((%s div pow(2,i)) mod 2)) * (((%s div pow(2,i)) mod 2))) | i in 0..%s]);
                         in\n""" %(sym,args[0],args[1],size-1))
        return sym

    def walk_bv_or(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        typeF=str(formula.get_type()).lower()       
        size=int(re.sub(r"bv{([0-9]+)}",r"\1",typeF))
        self.write(""" let { var int : %s  = sum([pow(2,i)* (((((%s div pow(2,i)) mod 2)) + (((%s div pow(2,i)) mod 2)))>0) | i in 0..%s]);
                       } in\n""" %(sym,args[0],args[1],size-1))
        return sym

    def walk_bv_not(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        typeF=str(formula.get_type()).lower()       
        size=int(re.sub(r"bv{([0-9]+)}",r"\1",typeF))
        self.write(""" let { var int : %s  = sum([pow(2,i)* (1-(%s div pow(2,i)) mod 2) | i in 0..%s]);
                       } in\n""" %(sym,args[0],size-1))
        return sym

    def walk_bv_xor(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        typeF=str(formula.get_type()).lower()       
        size=int(re.sub(r"bv{([0-9]+)}",r"\1",typeF))
        self.write(""" let { var int : %s  = sum([pow(2,i)* (((((%s div pow(2,i)) mod 2)) != (((%s div pow(2,i)) mod 2)))) | i in 0..%s]);
                       } in\n""" %(sym,args[0],args[1],size-1))
        return sym 

    def walk_bv_add(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1       
        size=formula.bv_width()  
        self.write("""let{ var int:%s = (%s+%s) mod %s;
                        } in\n"""%(sym,args[0],args[1],pow(2,size)))
        return sym

    def walk_bv_sub(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1       
        size=formula.bv_width()   
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                            var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                            var int:%s_ris = (%s_args1 - %s_args2) mod %s;
                            var int:%s = if %s_ris < 0 then %s_ris+%s else %s_ris endif;
                       } in\n""" %(sym,args[0],str(pow(2,size-1)),args[0],pow(2,size),args[0],
                                  sym,args[1],str(pow(2,size-1)),args[1],pow(2,size),args[1],
                                  sym,sym,sym,str(pow(2,size)),
                                  sym,sym,sym,str(pow(2,size)),sym))
        return sym

    def walk_bv_neg(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1   
        size=formula.bv_width()   
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                            var int:%s_ris = (0 - %s_args1);
                            var int:%s = if %s_ris < 0 then %s_ris+%s else %s_ris endif;
                        } in\n""" %(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,sym,
                                   sym,sym,sym,str(pow(2,size)),sym))
        return sym


    def walk_bv_mul(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        typeF=int(str(formula.get_type()).lower())       
        size=re.sub(r"bv{([0-9]+)}",r"\1",typeF)    
        self.write(""" let { var int:%s = (%s*%s) mod %s
                        } in\n"""%(sym,args[0],args[1],str(pow(2,size))))
        return sym

            

    def walk_bv_udiv(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1     
        self.write(""" let { var int:%s = (%s div %s)  
                       } in\n"""%(sym,args[0],args[1]))
        return sym

    def walk_bv_urem(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1  
        self.write(""" let { var int:%s = (%s mod %s)  
                        } in\n"""%(sym,args[0],args[1]))
        return sym


    def walk_bv_lshl(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        typeF=str(formula.get_type()).lower()       
        size=re.sub(r"bv{([0-9]+)}",r"\1",typeF)    
        self.write(""" let { var int:%s = (%s*pow(2,%s)) mod %s;
                        } in\n"""%(sym,args[0],args[1],str(pow(2,size))))
        return sym


    def walk_bv_lshr(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1        
        self.write(""" let { var int:%s = (%s div pow(2,%s))
                        } in\n"""%(sym,args[0],args[1]))
        return sym

    def walk_bv_ult(self, formula, args):    #depend on the encoding
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        self.write(""" let { var bool:%s = (%s<%s) 
                        } in\n"""%(sym,args[0],args[1]))
        return sym

    def walk_bv_ule(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        self.write(""" let { var bool:%s = (%s<=%s)
                       } in\n"""%(sym,args[0],args[1]))
        return sym

    def walk_bv_slt(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        size=int(formula.args()[0].bv_width())  
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                             var bool:%s = (%s_args1 < %s_args2)  
                        } in  """%(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,args[1],str(pow(2,size-1)),args[1],str(pow(2,size)),args[1],
                                   sym,sym,sym))
        return sym

    def walk_bv_sle(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        size=int(formula.args()[0].bv_width())  
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                             var bool:%s = (%s_args1 <= %s_args2)  
                        } in  """%(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,args[1],str(pow(2,size-1)),args[1],str(pow(2,size)),args[1],
                                   sym,sym,sym))
        return sym

    def walk_bv_concat(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        size_s1=formula.args()[0].bv_width()
        size_s2=formula.args()[1].bv_width()
        self.write(""" let { var int: %s = %s + sum([pow(2,i+%s)*(((%s div pow(2,i)) mod 2)) | i in 0..%s]);
                            } in\n"""%(sym,args[1],size_s2,args[0],size_s1-1))
        return sym

    def walk_bv_comp(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1   
        self.write(""" let { var int : %s  = if %s=%s then 1 else 0 endif;
                        } in\n""" %(sym,args[0],args[1]))
        return sym


    def walk_bv_ashr(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1    
        size=formula.bv_width() 
        self.write(""" let {  var int:%s_args1 = if %s>=%s then %s-%s+%s else %s endif;
                              var int:%s_ris =  %s_args1 div pow(2,%s);
                              var int:%s = if %s<%s  then %s_ris else sum([pow(2,i)*(((%s_ris+%s) div pow(2,i)) mod 2)|i in 0..%s]) endif;
                            } in\n"""%(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),str(pow(2,self.max_int_bit_size-1)),args[0], 
                                      sym,sym,args[1],
                                      sym,args[0],str(pow(2,size-1)),sym,sym,str(pow(2,self.max_int_bit_size-3)+pow(2,self.max_int_bit_size-2)+pow(2,self.max_int_bit_size-1)+pow(2,size)),size-1))
        return sym


    def walk_bv_sdiv(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1       
        size=formula.bv_width()   
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_ris = (%s_args1 div %s_args2);  
                             var int:%s = if %s_ris < 0 then %s_ris+%s else %s_ris endif;
                        } in\n""" %(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,args[1],str(pow(2,size-1)),args[1],str(pow(2,size)),args[1],
                                   sym,sym,sym,
                                   sym,sym,sym,str(pow(2,size)),sym))
        return sym

    def walk_bv_srem(self, formula, args):
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1       
        size=formula.bv_width()  #(sign follows dividend)
        self.write(""" let { var int:%s_args1 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_args2 = if %s >= %s then %s-%s else %s endif;
                             var int:%s_ris = (%s_args1 mod %s_args2);
                             var int:%s = if %s_ris < 0 then %s_ris+%s else %s_ris endif;
                        } in\n""" %(sym,args[0],str(pow(2,size-1)),args[0],str(pow(2,size)),args[0],
                                   sym,args[1],str(pow(2,size-1)),args[1],str(pow(2,size)),args[1],
                                   sym,sym,sym,
                                   sym,sym,sym,str(pow(2,size)),sym))
        return sym


    def walk_bv_tonatural(self, formula, args):
        # Kind of useless
        #return self.walk_nary(formula, args, "bv2nat")
        return """%s"""% (args[0])

    def walk_array_select(self, formula, args):
        return self.walk_nary(formula, args, "select")

    def walk_array_store(self, formula, args):
        return self.walk_nary(formula, args, "store")

    def walk_symbol(self, formula, **kwargs):
        return quote(formula.symbol_name())

    def walk_function(self, formula, args, **kwargs):
        return self.walk_nary(formula, args, formula.function_name())

    def walk_int_constant(self, formula, **kwargs):
        #print "INT CONSTANTANT ",formula.constant_value()
        if formula.constant_value() < 0:
            return "(- " + str(-formula.constant_value()) + ")"
        else:
            return str(formula.constant_value())

    def walk_real_constant(self, formula, **kwargs):
        #print "REAL CONSTANTANT ",formula.constant_value()
        #print "SIMPLY ",formula.constant_value.
        if formula.constant_value() < 0:
            template = "(- %s)"
        else:
            template = "%s"

        (n,d) = abs(formula.constant_value().numerator), \
                    formula.constant_value().denominator
        if d != 1:
            return template % ( "(" + str(n) + " / " + str(d) + ")" )
        else:
            return template % (str(n) + ".0")

    def walk_bv_constant(self, formula, **kwargs):
        return str(formula.constant_value())
        #return "#b" + res


    def walk_bool_constant(self, formula, **kwargs):
        if formula.constant_value():
            return "true"
        else:
            return "false"

    def walk_str_constant(self, formula, **kwargs):
        return '"' + formula.constant_value() + '"'

    def walk_forall(self, formula, args, **kwargs):
        #return self._walk_quantifier("forall", formula, args)
        raise NotImplementedErr("The forall operator cannot be translated into Mzn")

    def walk_exists(self, formula, args, **kwargs):
        #return self._walk_quantifier("exists", formula, args)
        raise NotImplementedErr("The exists operator cannot be translated into Mzn")

    def _walk_quantifier(self, operator, formula, args):
        raise NotImplementedErr("The quantifier cannot be translated into Mzn")

    def walk_bv_extract(self, formula, args, **kwargs):
        assert formula is not None
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        start=int(formula.bv_extract_start())
        end=int(formula.bv_extract_end())
        if start != end:
            self.write(""" let { var int : %s_s1 = %s div %s;
                                 var int : %s = sum([pow(2,i)*(((%s_s1 div pow(2,i)) mod 2)) | i in 0..%s])
                            } in\n"""%(sym,args[0],str(pow(2,start)),sym,sym,str(end-start)))
                                

        else:
            self.write(""" let { var int : %s =  (%s div pow(2,%s)) mod 2;
                            } in\n""" %(sym,args[0],start))
        return sym
    @handles(op.BV_SEXT, op.BV_ZEXT)
    def walk_bv_extend(self, formula, args, **kwargs):
        #pylint: disable=unused-argument
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        if formula.is_bv_zext():
            self.write(""" let { var int:%s = %s;  
                          } in\n"""%(sym,args[0]))
        else:
            assert formula.is_bv_sext() 
            self.write(""" let { var int:%s = %s+sum([pow(2,i) | i in %s..%s ]);  
                           } in\n"""%(sym,args[0],formula.args()[0].bv_width(),formula.bv_width()-1))
        return sym

    @handles(op.BV_ROR, op.BV_ROL)
    def walk_bv_rotate(self, formula, args, **kwargs):
        #pylint: disable=unused-argument
        sym=self._new_symbol_bv("bv_%d")
        self.openings += 1
        size=formula.bv_width()
        rotate=formula.bv_rotation_step()%size
        if formula.is_bv_ror():
            self.write(""" let { var int:%s = (%s div %s + ((%s * %s) mod %s)) mod %s;
                            } in\n"""%(sym,args[0],str(pow(2,rotate)),args[0],str(pow(2,size-rotate)),str(pow(2,size)),str(pow(2,size))))
        else:
            self.write(""" let { var int:%s = (%s div %s) + ((%s * %s mod %s)) mod %s; 
                           } in\n"""%(sym,args[0],str(pow(2,size-rotate)),args[0],str(pow(2,rotate)),str(pow(2,size)),str(pow(2,size))))
        
        return sym

    def walk_str_length(self, formula, args, **kwargs):
        #return "(str.len %s)" % args[0])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_charat(self,formula, args,**kwargs):
        #return "( str.at %s %s )" % (args[0], args[1])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_concat(self, formula, args, **kwargs):
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_contains(self,formula, args, **kwargs):
        #return "( str.contains %s %s)" % (args[0], args[1])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_indexof(self,formula, args, **kwargs):
        #return "( str.indexof %s %s %s )" % (args[0], args[1], args[2])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_replace(self,formula, args, **kwargs):
        #return "( str.replace %s %s %s )" % (args[0], args[1], args[2])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_substr(self,formula, args,**kwargs):
        #return "( str.substr %s %s %s)" % (args[0], args[1], args[2])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_prefixof(self,formula, args,**kwargs):
        #return "( str.prefixof %s %s )" % (args[0], args[1])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_suffixof(self,formula, args, **kwargs):
        #return "( str.suffixof %s %s )" % (args[0], args[1])
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_str_to_int(self,formula, args, **kwargs):
        #return "( str.to.int %s )" % args[0]
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_int_to_str(self,formula, args, **kwargs):
        #return "( int.to.str %s )" % args[0]
        raise NotImplementedErr("Operation that cannot be translated into MzN")

    def walk_array_value(self, formula, args, **kwargs):
        raise NotImplementedErr("Operation that cannot be translated into MzN")


class MZNPrinter(object):
    """Return the MZN version of the input formula"""
    def __init__(self,printer_selection,max_int_bit_size,environment=None):
        self.environment = environment
        self.last_index=0
        self.max_int_bit_size=max_int_bit_size
        self.printer_selection=printer_selection #0 simple daggify, 1 2fathers labeling

    def get_fathers(self,formula):
        cnt = 0
        fathers = collections.OrderedDict()
        seen = set()
        q = [formula]
        while q:
            e = q.pop()
            seen.add(e)
            for s in e.args():
                    if s.get_type()==BOOL and s in seen and s not in fathers and len(s.args())>=2:
                        fathers[s] = "tmp_"+str(cnt)
                        cnt+=1
                    q.append(s)
        return fathers


    def serialize(self,formula,daggify=True,output_file=None):
        if self.printer_selection==0:
            buf = cStringIO()
            if daggify:
                p = SmtDagPrinter(self.max_int_bit_size,buf)
            else:
                p = HRPrinter(buf)
            p.printer(formula)
            res=buf.getvalue()
        else:
            dict_f = self.get_fathers(formula)
            buf = cStringIO()
            str_let=""
            str_let_list=[]
            print dict_f
            if dict_f:
                k=dict_f.keys()
                dict_f_tmp=copy.copy(dict_f)
                for el in k:
                    dict_f.pop(el)
                    buf = cStringIO()
                    p = DagWalkerFathers(self.max_int_bit_size,buf,dict_f,boolean_invalidate=True)
                    p.printer(el)
                    dict_f=copy.copy(dict_f_tmp)
                    str_let_list.append(" var %s : %s =  %s;  \n "%(str(el.get_type()).lower().replace("real","float"),dict_f[el],buf.getvalue()))
            #temporary
            if str_let_list:
                str_let_list.sort(key=lambda x: x.count("tmp"))
                str_let = "let {\n"+"".join(str_let_list)+"} in \n"
            print dict_f
            buf = cStringIO()
            buf.write(str_let)
            p = DagWalkerFathers(self.max_int_bit_size,buf,dict_f,boolean_invalidate=False)
            p.printer(formula)
            res=buf.getvalue()
        if output_file is None:
            return res
        else:
            output_file.write("constraint ("+res+");\n")
        buf.close()

#EOC MZNPrinter

class NotImplementedErr(StandardError):
    pass