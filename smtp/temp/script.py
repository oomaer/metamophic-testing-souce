

from fandango.evolution.algorithm import Fandango, LoggerLevel
from fandango.io.navigation.coverage_goal import CoverageGoal
from fandango.language.grammar import FuzzingMode
from fandango.language.parse.parse import parse


import glob
import os


def run_fandango(grammar_path):

    print(f"Running Fandango with grammar: {grammar_path}")
    with open(grammar_path) as f:
        grammar, constraints = parse(f, use_stdlib=True)
    assert grammar is not None
    fandango = Fandango(
        grammar=grammar,
        constraints=constraints,
        logger_level=LoggerLevel.INFO,
        coverage_goal=CoverageGoal.STATE_INPUTS
    )
    solutions = fandango.generate(mode=FuzzingMode.IO)
    for solution in solutions:
        print(str(solution))


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fan_files = glob.glob(os.path.join(script_dir, "*.fan"))
    
    for fan_file in fan_files:
        if os.path.basename(fan_file) == "smtp-utils.fan":
            continue
        run_fandango(fan_file)
    

main()

