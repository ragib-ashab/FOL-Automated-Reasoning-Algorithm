# First-Order Logic Automated Reasoning Algorithm
*Developed for 3008ICT Assignment 1*

## Overview
Algorithm 2 from the textbook Fundamentals of Logic and Computation with Practical Automated Reasoning and Verification by Zhe Hou (Chapter 2.3, page 67), is a naïve backward proof search strategy for first-order logic using LK’. This algorithm is mathematically sound but is computationally flawed and frequently fails on more complex problems. Through testing datasets focused on combinatorial explosions, the algorithm goes into a loop and times out. The scope of this program is to implement and improve the automated reasoning Algorithm 2. 

## Key Improvements over Baseline
* **Breadth-First Search (BFS):** Replaces infinite-loop depth-first searches.
* **Cryptographic State Hashing:** Acts as a memory vault to prevent redundant state evaluations.
* **Non-Branching Saturation:** Forces deterministic logic processing before splitting the search tree, drastically reducing the search space.

## Datasets Included
* `Textbook Dataset`: Baseline mathematical soundness checks.

## Additional Tools Included
* `tptp_scraper.py`: A program to fetch benchmarking datasets from the TPTP SYN library.
* `problem_generator.py`: A program to generate custom datasets to stress test the baseline and improved algorithms.
  
## How to Run
1. Ensure Python 3.14.3 (or newer) is installed.
2. To test with large datasets, run the scraper or problem generator programs beforehand. Or, you can run the program immediately using the small included textbook dataset.
3. Execute the main program in the terminal:
`python prover.py`
