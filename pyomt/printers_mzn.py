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
from six.moves import cStringIO
import re
import pyomt.operators as op
from pyomt.walkers import TreeWalker,DagWalker
from pyomt.walkers.generic import handles
from pyomt.utils import quote
from pyomt.environment import get_env

from pyomt.constants import is_pyomt_fraction, is_pyomt_integer

class HRPrinter(TreeWalker):
    """Performs serialization of a formula in a human-readable way.

    E.g., Implies(And(Symbol(x), Symbol(y)), Symbol(z))  ~>   '(x * y) -> z'
    """

    def __init__(self, stream, id, env=None):
        TreeWalker.__init__(self, env=env)
        self.stream = stream
        self.write = self.stream.write
        self.fv=[]
        self.stack_subf=[]
        self.bv_sum=[]
        self.id=id
    
    def getId(self):
        #self.id+=1
        return self.id

    def printer(self, f,threshold=None):
        """Performs the serialization of 'f'.

        Thresholding can be used to define how deep in the formula to
        go. After reaching the thresholded value, "..." will be
        printed instead. This is mainly used for debugging.
        """
        self.walk(f,threshold=None)
        return self.bv_sum
                

    def walk_threshold(self, formula):
        self.write("...")

    def walk_nary(self, formula, ops):
        args = formula.args()
        if ops==" = " and len(args)==2 and "BV" in str(args[0].get_type()) and "BV" in str(args[1].get_type()):
            self.write("bveq(")
            yield args[0]
            self.write(",")
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
        """ old sytle
        self.write("sumBV(")
        yield formula.arg(0)
        self.write(",")
        yield formula.arg(1)
        self.write(")")
        """
        self.id+=1
        nameR = "R"+str(self.id)
        self.write(nameR)
        self.bv_sum.append((nameR,[formula.arg(0),formula.arg(1)]))



    
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
        return self.walk_quantifier("forall ", ", ", " . ", formula)

    def walk_exists(self, formula):
        return self.walk_quantifier("exists ", ", ", " . ", formula)

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
    
    def __init__(self, stream, id,template="tmp_%d"):
        DagWalker.__init__(self, invalidate_memoization=True)
        self.stream = stream
        self.write = self.stream.write
        self.openings = 0
        self.name_seed = 0
        self.template = template
        self.names = None
        self.mgr = get_env().formula_manager
        self.bv_sum=[]
        self.id=id

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
        return self.bv_sum
        #self.write(")")
    
    def getId(self):
        #self.id+=1
        return self.id

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
        #self.write("(let ((%s (%s" % (sym, operator))
        #self.write("(%s = ( " % (sym))
        typeF=str(formula.get_type()).lower().replace("real","float")
        if "bv" in typeF:
            size=re.sub(r"bv{([0-9]+)}",r"\1",typeF)
            self.write(" let{ array[1..%s] of var bool : %s = (" % (size,sym))
        else:
            self.write(" let{ var %s : %s = ( " % (typeF,sym))
        if operator=="bvadd":
            self.id+=1
            nameR = "R"+str(self.id)
            self.write(nameR)
            self.bv_sum.append((nameR,[formula.arg(0),formula.arg(1)]))
            self.write(" )} in  ")
        elif operator=="ite":
            self.write(" if ")
            self.write(args[0])
            self.write(" then ")
            self.write(args[1])
            self.write(" else ")
            self.write(args[2])
            self.write(" endif ")
            self.write(" )} in  ")
        elif operator in ["lex_less","lex_lesseq","bvslt","bvsle"]:
            self.write(" ")
            self.write(operator)
            self.write("(")
            self.write(args[0])
            self.write(",")
            self.write(args[1])
            self.write(")} in ")
        elif len(args)==1 and operator=="not":
            self.write(" ")
            self.write(" not (")
            self.write(args[0])
            self.write(")")
            self.write(" )} in  ")
        else:
            self.write(args[0])
            for s in args[1:]:
                self.write(" ")
                self.write(operator)
                self.write(" ")
                self.write(s)
            self.write(" )} in  ")
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
        return self.walk_nary(formula, args, "to_real")

    def walk_div(self, formula, args):
        return self.walk_nary(formula, args, "/")

    def walk_pow(self, formula, args):
        return self.walk_nary(formula, args, "pow")

    def walk_bv_and(self, formula, args):
        return self.walk_nary(formula, args, "bvand")

    def walk_bv_or(self, formula, args):
        return self.walk_nary(formula, args, "bvor")

    def walk_bv_not(self, formula, args):
        return self.walk_nary(formula, args, "bvnot")

    def walk_bv_xor(self, formula, args):
        return self.walk_nary(formula, args, "bvxor")

    def walk_bv_add(self, formula, args):
        return self.walk_nary(formula, args, "bvadd")

    def walk_bv_sub(self, formula, args):
        return self.walk_nary(formula, args, "bvsub")

    def walk_bv_neg(self, formula, args):
        return self.walk_nary(formula, args, "bvneg")

    def walk_bv_mul(self, formula, args):
        return self.walk_nary(formula, args, "bvmul")

    def walk_bv_udiv(self, formula, args):
        return self.walk_nary(formula, args, "bvudiv")

    def walk_bv_urem(self, formula, args):

        return self.walk_nary(formula, args, "bvurem")
    def walk_bv_lshl(self, formula, args):
        return self.walk_nary(formula, args, "bvshl")

    def walk_bv_lshr(self, formula, args):
        return self.walk_nary(formula, args, "bvlshr")

    def walk_bv_ult(self, formula, args):
        return self.walk_nary(formula, args, "lex_less")

    def walk_bv_ule(self, formula, args):
        return self.walk_nary(formula, args, "lex_lesseq")

    def walk_bv_slt(self, formula, args):
        return self.walk_nary(formula, args, "bvlst")

    def walk_bv_sle(self, formula, args):
        return self.walk_nary(formula, args, "bvsle")

    def walk_bv_concat(self, formula, args):
        return self.walk_nary(formula, args, "concat")

    def walk_bv_comp(self, formula, args):
        return self.walk_nary(formula, args, "bvcomp")

    def walk_bv_ashr(self, formula, args):
        return self.walk_nary(formula, args, "bvashr")

    def walk_bv_sdiv(self, formula, args):
        return self.walk_nary(formula, args, "bvsdiv")

    def walk_bv_srem(self, formula, args):
        return self.walk_nary(formula, args, "bvsrem")

    def walk_bv_tonatural(self, formula, args):
        return self.walk_nary(formula, args, "bv2nat")

    def walk_array_select(self, formula, args):
        return self.walk_nary(formula, args, "select")

    def walk_array_store(self, formula, args):
        return self.walk_nary(formula, args, "store")

    def walk_symbol(self, formula, **kwargs):
        return quote(formula.symbol_name())

    def walk_function(self, formula, args, **kwargs):
        return self.walk_nary(formula, args, formula.function_name())

    def walk_int_constant(self, formula, **kwargs):
        if formula.constant_value() < 0:
            return "(- " + str(-formula.constant_value()) + ")"
        else:
            return str(formula.constant_value())

    def walk_real_constant(self, formula, **kwargs):
        if formula.constant_value() < 0:
            template = "(- %s)"
        else:
            template = "%s"

        (n,d) = abs(formula.constant_value().numerator), \
                    formula.constant_value().denominator
        if d != 1:
            return template % ( "(/ " + str(n) + " " + str(d) + ")" )
        else:
            return template % (str(n) + ".0")

    def walk_bv_constant(self, formula, **kwargs):
        '''
        short_res = str(bin(formula.constant_value()))[2:]
        if formula.constant_value() >= 0:
            filler = "0"
        else:
            raise NotImplementedError
        res = short_res.rjust(formula.bv_width(), filler)
        '''
        bvsequence=str('{0:0'+str(formula.bv_width())+'b}').format(formula.constant_value())
        bvsequence_comma = re.sub(r'([0-1])(?!$)', r'\1,',bvsequence)
        bvsequence_comma_tf = bvsequence_comma.replace("0","false").replace("1","true")
        return "["+bvsequence_comma_tf+"]"
        #return "#b" + res


    def walk_bool_constant(self, formula, **kwargs):
        if formula.constant_value():
            return "true"
        else:
            return "false"

    def walk_str_constant(self, formula, **kwargs):
        return '"' + formula.constant_value() + '"'

    def walk_forall(self, formula, args, **kwargs):
        return self._walk_quantifier("forall", formula, args)

    def walk_exists(self, formula, args, **kwargs):
        return self._walk_quantifier("exists", formula, args)

    def _walk_quantifier(self, operator, formula, args):
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

        subprinter = SmtDagPrinter(self.stream)
        subprinter.printer(formula.arg(0))

        self.write(")))")
        return sym

    def walk_bv_extract(self, formula, args, **kwargs):
        """
        self.write("extractBV(")
        yield formula.arg(0)
        self.write(",%d,%d)" % (formula.bv_extract_start()+1,
                                       formula.bv_extract_end()+1))

        let{ var %s : %s = ( 
        """

        assert formula is not None
        sym = self._new_symbol()
        self.openings += 1
        self.write("let { array[1..%s] of var bool: %s = (" % (formula.bv_width, sym))
        #self.write("(let ((%s ((_ extract %d %d)" % (sym,
        #                                             formula.bv_extract_end(),
        #
        #                                             formula.bv_extract_start()))
        self.write("extractBV(%s,%s,%s)" % (args[0],formula.bv_extract_start(),formula.bv_extract_end()))
        self.write(" )} in ")
        #for s in args:
        #    self.write(" ")
        #    self.write(s)
        #self.write("))) ")
        return sym

    @handles(op.BV_SEXT, op.BV_ZEXT)
    def walk_bv_extend(self, formula, args, **kwargs):
        #pylint: disable=unused-argument
        if formula.is_bv_zext():
            extend_type = "zero_extend"
        else:
            assert formula.is_bv_sext()
            extend_type = "sign_extend"

        sym = self._new_symbol()
        self.openings += 1
        self.write("(let ((%s ((_ %s %d)" % (sym, extend_type,
                                                formula.bv_extend_step()))
        for s in args:
            self.write(" ")
            self.write(s)
        self.write("))) ")
        return sym

    @handles(op.BV_ROR, op.BV_ROL)
    def walk_bv_rotate(self, formula, args, **kwargs):
        #pylint: disable=unused-argument
        if formula.is_bv_ror():
            rotate_type = "rotate_right"
        else:
            assert formula.is_bv_rol()
            rotate_type = "rotate_left"

        sym = self._new_symbol()
        self.openings += 1
        self.write("(let ((%s ((_ %s %d)" % (sym, rotate_type,
                                             formula.bv_rotation_step()))
        for s in args:
            self.write(" ")
            self.write(s)
        self.write("))) ")
        return sym

    def walk_str_length(self, formula, args, **kwargs):
        return "(str.len %s)" % args[0]

    def walk_str_charat(self,formula, args,**kwargs):
        return "( str.at %s %s )" % (args[0], args[1])

    def walk_str_concat(self, formula, args, **kwargs):
        sym = self._new_symbol()
        self.openings += 1
        self.write("(let ((%s (%s" % (sym, "str.++ " ))
        for s in args:
            self.write(" ")
            self.write(s)
        self.write("))) ")
        return sym

    def walk_str_contains(self,formula, args, **kwargs):
        return "( str.contains %s %s)" % (args[0], args[1])

    def walk_str_indexof(self,formula, args, **kwargs):
        return "( str.indexof %s %s %s )" % (args[0], args[1], args[2])

    def walk_str_replace(self,formula, args, **kwargs):
        return "( str.replace %s %s %s )" % (args[0], args[1], args[2])

    def walk_str_substr(self,formula, args,**kwargs):
        return "( str.substr %s %s %s)" % (args[0], args[1], args[2])

    def walk_str_prefixof(self,formula, args,**kwargs):
        return "( str.prefixof %s %s )" % (args[0], args[1])

    def walk_str_suffixof(self,formula, args, **kwargs):
        return "( str.suffixof %s %s )" % (args[0], args[1])

    def walk_str_to_int(self,formula, args, **kwargs):
        return "( str.to.int %s )" % args[0]

    def walk_int_to_str(self,formula, args, **kwargs):
        return "( int.to.str %s )" % args[0]

    def walk_array_value(self, formula, args, **kwargs):
        sym = self._new_symbol()
        self.openings += 1
        self.write("(let ((%s " % sym)

        for _ in xrange((len(args) - 1) // 2):
            self.write("(store ")

        self.write("((as const %s) " % formula.get_type().as_smtlib(False))
        self.write(args[0])
        self.write(")")

        for i, k in enumerate(args[1::2]):
            self.write(" ")
            self.write(k)
            self.write(" ")
            self.write(args[2*i + 2])
            self.write(")")
        self.write("))")
        return sym



class MZNPrinter(object):
    """Return the serialized version of the formula as a string."""
       
    
    

    def __init__(self, environment=None):
        self.environment = environment
        self.last_index=0
        self.last_id=0

    def serialize(self, formula,daggify=True,file_out=None):
        """Returns a string with the human-readable version of the formula.

        'printer' is the printer to call to perform the serialization.
        'threshold' is the thresholding value for the printing function.
        """
        bv_sum=[]
        buf = cStringIO()
        if daggify:
            p = SmtDagPrinter(buf,self.last_id)
        else:
            p = HRPrinter(buf,self.last_id)
        bv_sum=p.printer(formula)
        res = buf.getvalue()
        if file_out is None: 
            return res
        else:
            bv_sum=self.print_bvsum_predicates(file_out,bv_sum)
            file_out.write("constraint ("+res+");\n")
            self.last_id=p.getId()
            self.last_index=len(bv_sum)
        buf.close()
        

    def print_bvsum_predicates(self,file_out,bv_sum):
        if len(bv_sum)>0:     
            while True:
                bv_sum_temp = bv_sum
                start_size= len(bv_sum)
                for el in bv_sum_temp:
                    bv_sum=p.printer(el[1][0])
                    if len(bv_sum)!=start_size: #ho inserito uno 
                        #self.last_id+=1
                        el[1][0] = "R"+str(p.getId()) #modifico l'ultimo
                        start_size=len(bv_sum) #ho chiamato sul primo e ho aggiunto uno size+1

                    bv_sum=p.printer(el[1][1])
                    if len(bv_sum)!=start_size: #non ho fatto il primo if
                        #self.last_id+=1
                        el[1][1] = "R"+str(p.getId())
                    
                if len(bv_sum)==len(bv_sum_temp):
                    break
        count=1
        last_used_size=None
        if len(bv_sum)>0:
            if "R" in str(bv_sum[0][1][0]) and "R" in str(bv_sum[0][1][1]):
                bv_sum.append(bv_sum[0])
                bv_sum.pop()
        for el1 in bv_sum:
            ris_var = el1[0]
            add_1=el1[1][0]
            add_2=el1[1][1]
            size=None
            if "R" not in str(add_1):
                if add_1.is_bv_constant():
                    size = add_1.bv_width()
                else:
                    tmp = str(add_1.get_type())
                    size = re.sub(r"BV{([0-9]+)}",r"\1",tmp)
                last_used_size=size
            elif "R" not in str(add_2):
                if add_2.is_bv_constant():
                    size = add_2.bv_width()
                else:
                    tmp = str(add_2.get_type())
                    size = re.sub(r"BV{([0-9]+)}",r"\1",tmp)
                last_used_size=size
            if size is None:
                 size=last_used_size
            index = ris_var.strip().split("R")[1]
            cstr ="C"+str(index)
            file_out.write("array [1.."+str(size)+"] of var bool: "+cstr+";\n" )
            file_out.write("array [1.."+str(size)+"] of var bool: "+ris_var+";\n")
            if "R" not in str(add_1):
                if add_1.is_bv_constant():
                    bvsequence=str('{0:0'+str(add_1.bv_width())+'b}').format(add_1.constant_value())
                    bvsequence_comma = re.sub(r'([0-1])(?!$)', r'\1,',bvsequence)
                    bvsequence_comma_tf = bvsequence_comma.replace("0","false").replace("1","true")
                    add_1_tw="["+bvsequence_comma_tf+"]"
                else:
                    add_1_tw=add_1
            else:
                add_1_tw=add_1
            if "R" not in str(add_2):
                if add_2.is_bv_constant():
                    bvsequence=str('{0:0'+str(add_2.bv_width())+'b}').format(add_2.constant_value())
                    bvsequence_comma = re.sub(r'([0-1])(?!$)', r'\1,',bvsequence)
                    bvsequence_comma_tf = bvsequence_comma.replace("0","false").replace("1","true")
                    add_2_tw="["+bvsequence_comma_tf+"]"
                else:
                    add_2_tw=add_2
            else:
                add_2_tw=add_2
            file_out.write("constraint ( sumBV("+str(add_1_tw)+","+str(add_2_tw)+","+cstr+","+ris_var+") );\n")
            #declare variable for result
            #declare variable for carry
            #retrieve the size
            count+=1
        return bv_sum
        

#EOC MZNPrinter

