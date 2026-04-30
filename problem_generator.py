import os
import csv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(CURRENT_DIR, "dataset", "generated")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_easy_chain(depth, var_id):
    premises = [f"p0_{var_id}()"]
    for i in range(depth):
        premises.append(f"( p{i}_{var_id}() => p{i+1}_{var_id}() )")

    left_side = premises[0]
    for p in premises[1:]:
        left_side = f"( {left_side} & {p} )"

    formula = f"( {left_side} => p{depth}_{var_id}() )"
    return formula

def generate_medium_branching(depth, var_id):
    left_side = f"( p0_{var_id}() => q0_{var_id}() )"
    for i in range(1, depth):
        left_side = f"( {left_side} & ( p{i}_{var_id}() => q{i}_{var_id}() ) )"
        
    right_ant = f"p0_{var_id}()"
    right_con = f"q0_{var_id}()"
    for i in range(1, depth):
        right_ant = f"( {right_ant} & p{i}_{var_id}() )"
        right_con = f"( {right_con} & q{i}_{var_id}() )"
        
    formula = f"( {left_side} => ( {right_ant} => {right_con} ) )"
    return formula

def generate_hard_tournament(depth, var_id):

    nodes = [f"n_{var_id}(c{i})" for i in range(depth)]
    node_str = nodes[0]
    for n in nodes[1:]:
        node_str = f"( {node_str} & {n} )"
        
    tourney = f"![X,Y]: ( ( n_{var_id}(X) & n_{var_id}(Y) ) => ( r_{var_id}(X,Y) | r_{var_id}(Y,X) ) )"
    
    trans = f"![X,Y,Z]: ( ( n_{var_id}(X) & ( n_{var_id}(Y) & n_{var_id}(Z) ) ) => ( ( r_{var_id}(X,Y) & r_{var_id}(Y,Z) ) => r_{var_id}(X,Z) ) )"
    
    axioms = f"( {node_str} & ( {tourney} & {trans} ) )"
    
    champ = f"?[X]: ( n_{var_id}(X) & ![Y]: ( n_{var_id}(Y) => r_{var_id}(X,Y) ) )"
    
    formula = f"( {axioms} => {champ} )"
    return formula


print("Starting synthetic data generation...")

GeneratedProblems = os.path.join(OUTPUT_DIR, "GeneratedProblems.p")
metadata_path = os.path.join(OUTPUT_DIR, "metadata.csv")


with open(GeneratedProblems, "w") as all_file, open(metadata_path, "w", newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["Problem_ID", "Difficulty", "Depth", "Variation", "Raw_Logic"])

    easy_filepath = os.path.join(OUTPUT_DIR, "easy_problems.txt")
    with open(easy_filepath, "w") as level_file:
        for depth in range(10, 20):
            for variation in range(10):
                pid = f"easy_d{depth}_v{variation}"
                logic = generate_easy_chain(depth, variation)
                tptp = f"fof({pid}, conjecture, {logic} ).\n"
                level_file.write(tptp)
                all_file.write(tptp)
                csv_writer.writerow([pid, "easy", depth, variation, logic])
    print("Success. Generated easy library: 100 problems.")

    medium_filepath = os.path.join(OUTPUT_DIR, "medium_problems.txt")
    with open(medium_filepath, "w") as level_file:
        for depth in range(4, 9):
            for variation in range(45):
                pid = f"medium_d{depth}_v{variation}"
                logic = generate_medium_branching(depth, variation)
                tptp = f"fof({pid}, conjecture, {logic} ).\n"
                level_file.write(tptp)
                all_file.write(tptp)
                csv_writer.writerow([pid, "medium", depth, variation, logic])
    print("Success. Generated medium library: 225 problems.")

    hard_filepath = os.path.join(OUTPUT_DIR, "hard_problems.txt")
    with open(hard_filepath, "w") as level_file:
        for depth in range(2, 6):
            for variation in range(100):
                pid = f"hard_d{depth}_v{variation}"
                logic = generate_hard_tournament(depth, variation)
                tptp = f"fof({pid}, conjecture, {logic} ).\n"
                level_file.write(tptp)
                all_file.write(tptp)
                csv_writer.writerow([pid, "hard", depth, variation, logic])
    print("Success. Generated hard library: 400 problems.")

print(f"All the problems are stored together as GeneratedProblems.p library: {GeneratedProblems}")
print(f"Success. Generated index: {metadata_path}")
