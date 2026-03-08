

# ======================
# Phase 1: Run Fadnango with spec header_list.fan -> Generates a list of header ["A", "B", "C"]
#          a, b, c
# Phase 2: gen_grammar.py -> Read list of header from pghase 1 and genrates grammar accordingly
#          <headers> :: = "a" <header_wo_a> | "b" <header_wo_b> | "c" <header_wo_c>
#         # <header_wo_a> :: = "b" <header_wo_ab> | "c" <header_wo_ac>
# Phase 3: Call fandango api with generated grammar 

# func gen
# find ::GEN_GRAMMER:: replaces mygengarmmer()

# call fandango api

# ======================


from fandango import constraints
from fandango.evolution.algorithm import Fandango, LoggerLevel
from fandango.io.navigation.coverage_goal import CoverageGoal
from fandango.language.grammar import FuzzingMode, grammar
from fandango.language.parse.parse import parse


from itertools import permutations as permute
from itertools import combinations
import tempfile
import subprocess
import os


total_grammers = 0
current_run = 1

def get_recipients():
    global total_grammers
    with open("/Users/i7949486/Downloads/docker/metamorphic-testing/mt-smtp/gen-recipients.fan") as f:
        grammar, constraints = parse(f, use_stdlib=False)
    assert grammar is not None
    fandango = Fandango(
        grammar=grammar,
        constraints=constraints,
        logger_level=LoggerLevel.ERROR,
    )

    recipients = []
    for solution in fandango.generate(mode=FuzzingMode.COMPLETE, max_generations=1):
        # print(str(solution))
        # print("-------------------------------------------------------------")
        recp_list_1, recp_list_2 = str(solution).split("|")
        
        recp_list_1 = recp_list_1.strip().split(",")[:-1]
        recp_list_2 = recp_list_2.strip().split(",")[:-1]

        recipients.append((recp_list_1, recp_list_2))


    recipients = recipients[:4] # limit to 5 runs for now
    total_grammers = len(recipients)
    return recipients

    


def covert_recipients_to_grammar(recipients):

    with open("/Users/i7949486/Downloads/docker/metamorphic-testing/mt-smtp/smtp-with-auth.fan") as f:
        grammar_str_orignal = f.read()

   
    for recp_list_1, recp_list_2 in recipients:
        grammar_str = grammar_str_orignal
        recp_sequence_A = ""
        recp_sequence_B = ""
       
        for i, recp in enumerate(recp_list_1):
            recp_sequence_A += f"<ClientA:request_rcpt_to_{i+1}><ServerA:response_rcpt_to>"
            # create new non-terminals for each recipient
            grammar_str += f"<request_rcpt_to_{i+1}> ::= 'RCPT TO:{recp}\\r\\n'\n"
        for i, recp in enumerate(recp_list_2):
            recp_sequence_B += f"<ClientB:request_rcpt_to_{len(recp_list_1)+i+1}><ServerB:response_rcpt_to>"
            grammar_str += f"<request_rcpt_to_{len(recp_list_1)+i+1}> ::= 'RCPT TO:{recp}\\r\\n'\n"
        
        grammar_str = grammar_str.replace("<rcpt_sequence_A> ::= ->Generated from fuzzer and replaced here with python script->", f"<rcpt_sequence_A> ::= {recp_sequence_A}")
        grammar_str = grammar_str.replace("<rcpt_sequence_B> ::= ->Generated from fuzzer and replaced here with python script->", f"<rcpt_sequence_B> ::= {recp_sequence_B}")
       
        # write grammer_str to temporary file in same path/temp folder and run fandango with that grammer
        script_dir = os.path.dirname(os.path.abspath(__file__))
        temp_dir = os.path.join(script_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=True, suffix=".fan", dir=temp_dir) as tmp_file:
            tmp_file.write(grammar_str.encode())
            tmp_file_path = tmp_file.name
            run_fandango(tmp_file_path)
        # run_fandango_from_cmd(tmp_file_path)

        
 
def run_fandango(grammar_path):
    global current_run
    fandango = None
    print(f" ---------------------------------Curernt run: {current_run}, Total grammers: {total_grammers} --------------------------------")
    print("-------------------------------------------------------------")
    print("-------------------------------------------------------------")
    print(f"Running Fandango with grammar: {grammar_path}")
    with open(grammar_path) as f:
        grammar, constraints = parse(f, use_stdlib=False)
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
        print("-------------------------------------------------------------")
        # break
    
    current_run += 1



def run_fandango_from_cmd(grammar_path):
    global current_run
    print(f" ---------------------------------Curernt run: {current_run}, Total grammers: {total_grammers} --------------------------------")
    print("-------------------------------------------------------------")
    print("-------------------------------------------------------------")
    process = subprocess.Popen(
        ['fandango', '-v', 'talk', '-f', grammar_path, '-n', '1'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    for line in process.stdout:
        print(line, end='', flush=True)
    
    process.wait()
    print(f"Return code: {process.returncode}")
    current_run += 1


def main():
    recps = get_recipients()
    covert_recipients_to_grammar(recps)
    

main()




# why not run a grammer with client and server again and again
# can we use <ClientA:"string here"> directly


# how good is fandango in testing protocols.
# can you test metamorphic relations spanning across multiple states with fandango?