import os
import re
import sys
import time
from collections import deque
from typing import List, Tuple, Dict, Set, Optional


#Custom ASTs
class Formula:
    def __eq__(self, other):
        return isinstance(other, type(self)) and self._key() == other._key()
    def __hash__(self):
        return hash(self._key())
    def _key(self):
        return str(self)

class Top(Formula):
    def __str__(self): return "$true"
    def _key(self): return "TOP"

class Bottom(Formula):
    def __str__(self): return "$false"
    def _key(self): return "BOTTOM"

class Pred(Formula):
    def __init__(self, name: str, args: List[str] = None):
        self.name = name
        self.args = args or []
    def __str__(self):
        return f"{self.name}({','.join(self.args)})" if self.args else self.name
    def _key(self): return ("PRED", self.name, tuple(self.args))

class Not(Formula):
    def __init__(self, arg: Formula):
        self.arg = arg
    def __str__(self): return f"~{self.arg}"
    def _key(self): return ("NOT", self.arg._key())

class And(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    def __str__(self): return f"({self.left} & {self.right})"
    def _key(self): return ("AND", self.left._key(), self.right._key())

class Or(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    def __str__(self): return f"({self.left} | {self.right})"
    def _key(self): return ("OR", self.left._key(), self.right._key())

class Implies(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    def __str__(self): return f"({self.left} => {self.right})"
    def _key(self): return ("IMP", self.left._key(), self.right._key())

class ForAll(Formula):
    def __init__(self, vars: List[str], arg: Formula):
        self.vars = vars
        self.arg = arg
    def __str__(self): return f"![{','.join(self.vars)}]: {self.arg}"
    def _key(self): return ("FORALL", tuple(self.vars), self.arg._key())

class Exists(Formula):
    def __init__(self, vars: List[str], arg: Formula):
        self.vars = vars
        self.arg = arg
    def __str__(self): return f"?[{','.join(self.vars)}]: {self.arg}"
    def _key(self): return ("EXISTS", tuple(self.vars), self.arg._key())


#Parser and Data Loader
def tokenize(formula_str: str) -> List[str]:
    s = formula_str.replace("=>", " IMPLIES ").replace("<=>", " IFF ")
    s = s.replace("!=", " NOT_EQ ").replace("~", " ~ ")
    for ch in "()[]:,=":
        s = s.replace(ch, f" {ch} ")
    s = s.replace("NOT_EQ", " != ")
    s = s.replace("IMPLIES", "=>")
    s = s.replace("IFF", "<=>")
    
    s = s.replace("&", " & ").replace("|", " | ")
    return [t for t in s.split() if t]

def parse_term(tokens: List[str]) -> str:
    name = tokens.pop(0)
    if tokens and tokens[0] == "(":
        tokens.pop(0)
        args = []
        while tokens and tokens[0] != ")":
            args.append(parse_term(tokens))
            if tokens and tokens[0] == ",":
                tokens.pop(0)
        if tokens and tokens[0] == ")":
            tokens.pop(0)
        return f"{name}({','.join(args)})"
    return name

def parse_implies(tokens: List[str]) -> Formula:
    left = parse_or(tokens)
    while tokens and tokens[0] == "=>":
        tokens.pop(0)
        right = parse_implies(tokens)
        left = Implies(left, right)
    return left

def parse_or(tokens: List[str]) -> Formula:
    left = parse_and(tokens)
    while tokens and tokens[0] == "|":
        tokens.pop(0)
        right = parse_and(tokens)
        left = Or(left, right)
    return left

def parse_and(tokens: List[str]) -> Formula:
    left = parse_not_quant(tokens)
    while tokens and tokens[0] == "&":
        tokens.pop(0)
        right = parse_not_quant(tokens)
        left = And(left, right)
    return left

def parse_not_quant(tokens: List[str]) -> Formula:
    if not tokens:
        raise ValueError("Unexpected end of formula")

    tok = tokens[0]

    if tok in ("$true", "True"):
        tokens.pop(0)
        return Top()
    if tok in ("$false", "False"):
        tokens.pop(0)
        return Bottom()

    if tok == "~":
        tokens.pop(0)
        return Not(parse_not_quant(tokens))

    if tok in ("!", "?"):
        q = tokens.pop(0)
        if not tokens or tokens[0] != "[":
            raise ValueError(f"Expected '[' after quantifier '{q}'")
        tokens.pop(0)

        vars_list = []
        while tokens and tokens[0] != "]":
            v = tokens.pop(0)
            if v != ",":
                vars_list.append(v)
        if tokens and tokens[0] == "]":
            tokens.pop(0)
        if tokens and tokens[0] == ":":
            tokens.pop(0)

        body = parse_not_quant(tokens)
        return ForAll(vars_list, body) if q == "!" else Exists(vars_list, body)

    if tok == "(":
        tokens.pop(0)
        expr = parse_implies(tokens)
        if tokens and tokens[0] == ")":
            tokens.pop(0)
        else:
            raise ValueError("Missing closing ')'")
        return expr

    name = tokens.pop(0)
    args = []
    if tokens and tokens[0] == "(":
        tokens.pop(0)
        while tokens and tokens[0] != ")":
            args.append(parse_term(tokens))
            if tokens and tokens[0] == ",":
                tokens.pop(0)
        if tokens and tokens[0] == ")":
            tokens.pop(0)
        else:
            raise ValueError("Missing closing ')' in predicate arguments")

    if tokens and tokens[0] in ("=", "!="):
        op = tokens.pop(0)
        right_term = parse_term(tokens)
        
        left_term = name
        if args:
            left_term = f"{name}({','.join(args)})"
            
        eq_pred = Pred("eq", [left_term, right_term])
        return eq_pred if op == "=" else Not(eq_pred)

    return Pred(name, args)

def parse_formula(tokens: List[str]) -> Formula:
    return parse_implies(tokens)

def extract_formula(line: str) -> Optional[str]:
    line = line.strip()
    if not line.startswith("fof("): return None
    if line.endswith(")."): line = line[:-2]
    elif line.endswith(")"): line = line[:-1]
    parts = line.split(",", 2)
    if len(parts) < 3: return None
    return parts[2].strip()

def load_file(filepath: str) -> Tuple[List[Formula], List[Formula]]:
    axioms, conjectures = [], []
    with open(filepath, "r") as f:
        content = f.read()
    content = re.sub(r"%.*", "", content)
    content = " ".join(content.split())
    for match in re.finditer(r"fof\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*(.+?)\s*\)\s*\.", content):
        name, role, formula_str = match.groups()
        role = role.strip().lower()
        formula_str = formula_str.strip()

        if "<=>" in formula_str or "<->" in formula_str:
            continue

        if formula_str:
            formula_str = f"({formula_str})"

        try:
            tokens = tokenize(formula_str)
            ast = parse_formula(tokens)
            if role == "conjecture":
                conjectures.append(ast)
            else:
                axioms.append(ast)
        except Exception as e:
            pass
    return axioms, conjectures


#Helper functions
def allTerm(formula: Formula) -> Set[str]:
    if isinstance(formula, (Top, Bottom)): return set()
    if isinstance(formula, Pred): return set(formula.args) if formula.args else {formula.name}
    if isinstance(formula, Not): return allTerm(formula.arg)
    if isinstance(formula, (And, Or, Implies)): return allTerm(formula.left) | allTerm(formula.right)
    if isinstance(formula, (ForAll, Exists)): return allTerm(formula.arg) - set(formula.vars)
    return set()

def substitute(formula: Formula, var: str, term: str) -> Formula:
    if isinstance(formula, (Top, Bottom)): return formula
    if isinstance(formula, Pred):
        new_args = [term if a == var else a for a in formula.args]
        return Pred(formula.name, new_args)
    if isinstance(formula, Not): return Not(substitute(formula.arg, var, term))
    if isinstance(formula, (And, Or, Implies)):
        left = substitute(formula.left, var, term)
        right = substitute(formula.right, var, term)
        if isinstance(formula, And): return And(left, right)
        if isinstance(formula, Or): return Or(left, right)
        return Implies(left, right)
    if isinstance(formula, (ForAll, Exists)):
        if var in formula.vars: return formula
        new_arg = substitute(formula.arg, var, term)
        if isinstance(formula, ForAll): return ForAll(formula.vars, new_arg)
        return Exists(formula.vars, new_arg)
    return formula

def unrollQuant(formula: Formula, term: str) -> Formula:
    if not isinstance(formula, (ForAll, Exists)) or not formula.vars: return formula
    var = formula.vars[0]
    rest_vars = formula.vars[1:]
    new_body = substitute(formula.arg, var, term)
    if not rest_vars: return new_body
    if isinstance(formula, ForAll): return ForAll(rest_vars, new_body)
    return Exists(rest_vars, new_body)

def sequentKey(gamma: List[Formula], delta: List[Formula]) -> Tuple[Tuple, Tuple]:
    g_str = tuple(sorted(str(f) for f in gamma))
    d_str = tuple(sorted(str(f) for f in delta))
    return (g_str, d_str)

def isClosed(gamma: List[Formula], delta: List[Formula]) -> bool:
    gamma_set = {str(f) for f in gamma}
    delta_set = {str(f) for f in delta}
    if gamma_set & delta_set: return True
    if any(isinstance(f, Bottom) for f in gamma): return True
    if any(isinstance(f, Top) for f in delta): return True
    return False

def allTerm_list(formulas: List[Formula]) -> Set[str]:
    terms = set()
    for f in formulas: terms.update(allTerm(f))
    return terms


#Algorithm 2 from Fundamentals of Logic and Computation With Practical Automated Reasoning and Verification by Zhe Hou. Chapter 2.3, Page 67 
def checkClosure(gamma, delta):
    for g in gamma:
        for d in delta:
            if g == d: return True
    for g in gamma:
        if isinstance(g, Bottom): return True
    for d in delta:
        if isinstance(d, Top): return True
    return False

def algorithm2(axioms: List[Formula], conjectures: List[Formula], time_limit_ms: int = 10000, max_depth: int = 60) -> bool:
    start_time = time.time()
    
    # Build the bottom sequent using your parsed axioms and conjectures
    gamma_init = list(axioms)
    delta_init = list(conjectures)
    
    open_branches = [(gamma_init, delta_init, {})]
    depth = 0
    
    while open_branches and depth < max_depth:
        new_open_branches = []
        
        # foreach top sequent on an open branch do
        for gamma, delta, used_terms in open_branches:
            
            # Enforce the benchmark timeout limit
            if (time.time() - start_time) * 1000 > time_limit_ms:
                return False
                
            # if any of the rules id, ⊤R and ⊥L is applicable then
            if checkClosure(gamma, delta):
                # apply the rule backwards and close the branch
                continue
            
            applied = False
            
            # else if any of the rules ∧L, ∨R, →R, ¬L, ¬R, ∀R and ∃L then
            for i, f in enumerate(gamma):
                if isinstance(f, And):
                    new_gamma = gamma[:i] + gamma[i+1:] + [f.left, f.right]
                    new_open_branches.append((new_gamma, delta, used_terms.copy()))
                    applied = True
                    break
                if isinstance(f, Not):
                    new_gamma = gamma[:i] + gamma[i+1:]
                    new_delta = delta + [f.arg]
                    new_open_branches.append((new_gamma, new_delta, used_terms.copy()))
                    applied = True
                    break
                if isinstance(f, Exists):
                    fresh = f"fresh_{depth}"
                    new_gamma = gamma[:i] + gamma[i+1:] + [unrollQuant(f, fresh)]
                    new_open_branches.append((new_gamma, delta, used_terms.copy()))
                    applied = True
                    break
            
            if not applied:
                for i, f in enumerate(delta):
                    if isinstance(f, Or):
                        new_delta = delta[:i] + delta[i+1:] + [f.left, f.right]
                        new_open_branches.append((gamma, new_delta, used_terms.copy()))
                        applied = True
                        break
                    if isinstance(f, Implies):
                        new_gamma = gamma + [f.left]
                        new_delta = delta[:i] + delta[i+1:] + [f.right]
                        new_open_branches.append((new_gamma, new_delta, used_terms.copy()))
                        applied = True
                        break
                    if isinstance(f, Not):
                        new_gamma = gamma + [f.arg]
                        new_delta = delta[:i] + delta[i+1:]
                        new_open_branches.append((new_gamma, new_delta, used_terms.copy()))
                        applied = True
                        break
                    if isinstance(f, ForAll):
                        fresh = f"fresh_{depth}"
                        new_delta = delta[:i] + delta[i+1:] + [unrollQuant(f, fresh)]
                        new_open_branches.append((gamma, new_delta, used_terms.copy()))
                        applied = True
                        break
            
            if applied:
                # apply the rule backwards
                continue
            
            # else if any of the rules ∧R, ∨L and →L is applicable then
            for i, f in enumerate(gamma):
                if isinstance(f, Or):
                    left = gamma[:i] + gamma[i+1:] + [f.left]
                    right = gamma[:i] + gamma[i+1:] + [f.right]
                    new_open_branches.append((left, delta, used_terms.copy()))
                    new_open_branches.append((right, delta, used_terms.copy()))
                    applied = True
                    break
                if isinstance(f, Implies):
                    left = gamma[:i] + gamma[i+1:]
                    new_delta_left = delta + [f.left]
                    right = gamma[:i] + gamma[i+1:] + [f.right]
                    new_open_branches.append((left, new_delta_left, used_terms.copy()))
                    new_open_branches.append((right, delta, used_terms.copy()))
                    applied = True
                    break
            
            if not applied:
                for i, f in enumerate(delta):
                    if isinstance(f, And):
                        left = delta[:i] + delta[i+1:] + [f.left]
                        right = delta[:i] + delta[i+1:] + [f.right]
                        new_open_branches.append((gamma, left, used_terms.copy()))
                        new_open_branches.append((gamma, right, used_terms.copy()))
                        applied = True
                        break
            
            if applied:
                # apply the rule backwards and create a new branch
                continue
            
            # Collect terms for instantiation
            all_terms = set()
            for f in gamma + delta:
                all_terms.update(allTerm(f))
            if not all_terms:
                all_terms = {"c0"}
            
            # else if ∀L or ∃R is applicable and there is a term t which has not been used 
            # to instantiate the quantified variable x in said formula then
            for i, f in enumerate(gamma):
                if isinstance(f, ForAll):
                    qf_key = str(f)
                    tried = used_terms.get(qf_key, set())
                    for term in all_terms:
                        if term not in tried:
                            new_gamma = gamma + [unrollQuant(f, term)]
                            new_used = used_terms.copy()
                            new_used[qf_key] = tried | {term}
                            new_open_branches.append((new_gamma, delta, new_used))
                            applied = True
                            break
                    if applied: break
                    
            if not applied:
                for i, f in enumerate(delta):
                    if isinstance(f, Exists):
                        qf_key = str(f)
                        tried = used_terms.get(qf_key, set())
                        for term in all_terms:
                            if term not in tried:
                                new_delta = delta + [unrollQuant(f, term)]
                                new_used = used_terms.copy()
                                new_used[qf_key] = tried | {term}
                                new_open_branches.append((gamma, new_delta, new_used))
                                applied = True
                                break
                        if applied: break
            
            if applied:
                # apply the rule backwards by substituting x with t
                continue
            
            # else if ∀L or ∃R is applicable then
            for i, f in enumerate(gamma):
                if isinstance(f, ForAll):
                    fresh = f"fresh_{depth}"
                    new_gamma = gamma + [unrollQuant(f, fresh)]
                    new_used = used_terms.copy()
                    new_used[str(f)] = used_terms.get(str(f), set()) | {fresh}
                    new_open_branches.append((new_gamma, delta, new_used))
                    applied = True
                    break
                    
            if not applied:
                for i, f in enumerate(delta):
                    if isinstance(f, Exists):
                        fresh = f"fresh_{depth}"
                        new_delta = delta + [unrollQuant(f, fresh)]
                        new_used = used_terms.copy()
                        new_used[str(f)] = used_terms.get(str(f), set()) | {fresh}
                        new_open_branches.append((gamma, new_delta, new_used))
                        applied = True
                        break
                        
            if applied:
                # apply the rule backwards and create a fresh term
                continue
            
            # else stop
            return False
            
        open_branches = new_open_branches
        depth += 1
        
    return len(open_branches) == 0


#Improved Algortihm2 using Breadth first Search and saturation.
def saturate(gamma: List[Formula], delta: List[Formula], used: Dict[str, Set[str]], start_time: float, time_limit_ms: int) -> Tuple[List[Formula], List[Formula], Dict[str, Set[str]], bool]:
    changed = True
    while changed:
        if (time.time() - start_time) * 1000 > time_limit_ms:
            return gamma, delta, used, False
            
        changed = False
        for i, f in enumerate(gamma):
            if isinstance(f, Not):
                gamma = gamma[:i] + gamma[i+1:]
                delta = delta + [f.arg]
                changed = True
                break
            if isinstance(f, And):
                gamma = gamma[:i] + gamma[i+1:] + [f.left, f.right]
                changed = True
                break
            if isinstance(f, Exists):
                fresh = f"sk_sat_{len(used)}"
                gamma = gamma[:i] + gamma[i+1:] + [unrollQuant(f, fresh)]
                changed = True
                break
        if changed: continue
        for i, f in enumerate(delta):
            if isinstance(f, Not):
                delta = delta[:i] + delta[i+1:]
                gamma = gamma + [f.arg]
                changed = True
                break
            if isinstance(f, Or):
                delta = delta[:i] + delta[i+1:] + [f.left, f.right]
                changed = True
                break
            if isinstance(f, Implies):
                delta = delta[:i] + delta[i+1:] + [f.right]
                gamma = gamma + [f.left]
                changed = True
                break
            if isinstance(f, ForAll):
                fresh = f"sk_sat_{len(used)}"
                delta = delta[:i] + delta[i+1:] + [unrollQuant(f, fresh)]
                changed = True
                break
        if changed: continue
    return gamma, delta, used, True

def bfs(axioms, conjectures, term_limit, max_depth, start_time, time_limit_ms):
    gamma = list(axioms)
    delta = list(conjectures)
    used = {}
    visited = set()
    term_pool = list(allTerm_list(gamma + delta))
    if not term_pool:
        term_pool = ["c0"]

    queue = deque([(gamma, delta, used, 0)])

    while queue:
        if (time.time() - start_time) * 1000 > time_limit_ms:
            return "TIMEOUT"
        
        gamma, delta, used, depth = queue.popleft()
        if depth > max_depth:
            continue
            
        key = sequentKey(gamma, delta)
        if key in visited:
            continue
        visited.add(key)

        if isClosed(gamma, delta):
            continue

        gamma, delta, used, safe = saturate(gamma, delta, used, start_time, time_limit_ms)
        if not safe: return "TIMEOUT"
        if isClosed(gamma, delta): continue
            
        key = sequentKey(gamma, delta)
        if key in visited: continue
        visited.add(key)

        applied = False

        for i, f in enumerate(gamma):
            if isinstance(f, Or):
                queue.append((gamma[:i] + gamma[i+1:] + [f.left], delta, used.copy(), depth + 1))
                queue.append((gamma[:i] + gamma[i+1:] + [f.right], delta, used.copy(), depth + 1))
                applied = True
                break
            if isinstance(f, Implies):
                queue.append((gamma[:i] + gamma[i+1:], delta + [f.left], used.copy(), depth + 1))
                queue.append((gamma[:i] + gamma[i+1:] + [f.right], delta, used.copy(), depth + 1))
                applied = True
                break
        if applied: continue

        # Branching rules for the right side
        for i, f in enumerate(delta):
            if isinstance(f, And):
                queue.append((gamma, delta[:i] + delta[i+1:] + [f.left], used.copy(), depth + 1))
                queue.append((gamma, delta[:i] + delta[i+1:] + [f.right], used.copy(), depth + 1))
                applied = True
                break
        if applied: continue

        dynamic_pool = list(allTerm_list(gamma + delta))
        if not dynamic_pool: 
            dynamic_pool = ["c0"]
        current_terms = dynamic_pool + [f"sk_{k}" for k in range(term_limit)]
        sides = [('gamma', gamma), ('delta', delta)]
        if depth % 2 != 0:
            sides = [('delta', delta), ('gamma', gamma)]

        for side_name, side_formulas in sides:
            if applied: 
                break
            
            for i, f in enumerate(side_formulas):
                is_valid = (side_name == 'gamma' and isinstance(f, ForAll)) or \
                           (side_name == 'delta' and isinstance(f, Exists))
                
                if is_valid:
                    qkey = str(f)
                    tried = used.get(qkey, set())
                    
                    if len(tried) >= term_limit: 
                        continue
                    
                    for t in current_terms:
                        if t not in tried:
                            new_used = used.copy()
                            new_used[qkey] = tried | {t}
                            if side_name == 'gamma':
                                queue.append((gamma + [unrollQuant(f, t)], delta, new_used, depth + 1))
                            else:
                                queue.append((gamma, delta + [unrollQuant(f, t)], new_used, depth + 1))
                            applied = True
                            break
                    break

        if not applied:
            return False 
        
    return True

def improved_algorithm2(axioms: List[Formula], conjectures: List[Formula], time_limit_ms: int = 10000, max_depth: int = 60) -> bool:
    start_time = time.time()

    for current_limit in range(1, 11):
        elapsed = (time.time() - start_time) * 1000
        if elapsed > time_limit_ms:
            return False
            
        result = bfs(axioms, conjectures, current_limit, max_depth, start_time, time_limit_ms)
        
        if result is True:
            return True
        if result == "TIMEOUT":
            return False
    return False

# Benchmark
if __name__ == "__main__":
    print()
    print("="*50)
    print("[PREREQUISITE] Ensure dataset folders contain .p files.")
    print("[INFO] A Scraper and Problem Generator script is available to populate the dataset folders.")
    print("[INFO] A default Textbook dataset is included for quick verification.")
    print("-" * 50)
    print("\nSelect the benchmark dataset to run:")
    print("1. Textbook Problems Dataset ")
    print("2. TPTP SYN Dataset")
    print("3. Custom Generated Problems Dataset")
    
    choice = input("Enter 1, 2, or 3: ").strip()
    
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    if choice == "1":
        DATASET_DIR = os.path.join(CURRENT_DIR, "dataset", "textbook")
        print("\nRunning Benchmark with Textbook Problems Dataset...")
    elif choice == "2":
        DATASET_DIR = os.path.join(CURRENT_DIR, "dataset", "SYN")
        print("\nRunning Benchmark with TPTP SYN Dataset...")
    elif choice == "3":
        DATASET_DIR = os.path.join(CURRENT_DIR, "dataset", "generated")
        print("\nRunning Benchmark with Custom Generated Problems Dataset...")
    else:
        print("Invalid selection. Exiting program.")
        sys.exit()
    
    print(f"\n{'Filename':<20} | {'Base Result':<12} | {'Base Time (ms)':<15} | {'Imp Result':<12} | {'Imp Time (ms)':<15}")
    print("-" * 85)

    valid_file_count = 0
    base_solved_count = 0
    imp_solved_count = 0
    total_base_time = 0.0
    total_imp_time = 0.0

    if not os.path.exists(DATASET_DIR):
        print(f"Directory {DATASET_DIR} not found. Please verify folder structure.")
    else:
        for filename in os.listdir(DATASET_DIR):
            if filename.endswith(".p"):
                filepath = os.path.join(DATASET_DIR, filename)
                
                axioms, conjectures = load_file(filepath)
                
                if choice == "2":
                    if not conjectures: 
                        continue
                    valid_file_count += 1
                    
                    start_base = time.time()
                    res_base = algorithm2(axioms, conjectures)
                    time_base = (time.time() - start_base) * 1000
                    
                    start_imp = time.time()
                    res_imp = improved_algorithm2(axioms, conjectures)
                    time_imp = (time.time() - start_imp) * 1000
                    
                    if res_base: base_solved_count += 1
                    if res_imp: imp_solved_count += 1
                    total_base_time += time_base
                    total_imp_time += time_imp
                    
                    print(f"{filename:<20} | {str(res_base):<12} | {time_base:<15.2f} | {str(res_imp):<12} | {time_imp:<15.2f}")

                elif choice in ("1", "3"):
                    for index, conjecture in enumerate(conjectures):
                        valid_file_count += 1
                        
                        start_base = time.time()
                        res_base = algorithm2([], [conjecture], time_limit_ms=10000, max_depth=60)
                        time_base = (time.time() - start_base) * 1000
                        
                        start_imp = time.time()
                        res_imp = improved_algorithm2([], [conjecture], time_limit_ms=10000, max_depth=60)
                        time_imp = (time.time() - start_imp) * 1000
                        
                        if res_base: base_solved_count += 1
                        if res_imp: imp_solved_count += 1
                        total_base_time += time_base
                        total_imp_time += time_imp
                        
                        if choice == "1":
                            display_name = f"Textbook Problem [{valid_file_count}]"
                        else:
                            display_name = f"Generated Problem [{valid_file_count}]"
                            
                        print(f"{display_name:<20} | {str(res_base):<12} | {time_base:<15.2f} | {str(res_imp):<12} | {time_imp:<15.2f}")

        print("-" * 85)
        print("=== FINAL BENCHMARK SUMMARY ===")
        print(f"Total Usable FOF Problems Parsed: {valid_file_count}")
        print(f"Baseline Solver: Solved {base_solved_count}/{valid_file_count} problems. Total execution time: {total_base_time:.2f} ms")
        print(f"Improved Solver: Solved {imp_solved_count}/{valid_file_count} problems. Total execution time: {total_imp_time:.2f} ms")