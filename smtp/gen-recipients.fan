
import random

def get_mutation(order):
    hash_id = hash(order.get_root())
    recps = [h.strip() for h in order.split(',') if h.strip()]
    # Use the hash as a seed for deterministic permutation
    # Ensure the seed is positive and within a reasonable range
    seed = abs(hash_id) % (2**31 - 1)
    
    # Create a random number generator with the seed
    rng = random.Random(seed)
    
    # Create a copy and shuffle it deterministically
    permuted_recps = recps.copy()
    rng.shuffle(permuted_recps)
    
    # Return the permutation as a comma-separated string
    # return ','.join(permuted_headers)
    permuted_recp = (",".join(permuted_recps) + ",")
    return permuted_recp
   
    
    
   
<start> ::= <recp_list_1> "|" <recp_list_2>

<recp_list_1>::= <recp_comp><recp_comp>
<recp_list_2> ::= <recp_comp><recp_comp>
<recp_comp> ::= (<recp> ",") | (<recp> "," <recp_comp>)

<recp> ::= "<recipient1@example.com>" | "<recipient2@example.com>" | "<recipient3@example.com>"


where str(<recp_list_1>) == get_mutation(<recp_list_2>)
where str(<recp_list_1>) != str(<recp_list_2>)
