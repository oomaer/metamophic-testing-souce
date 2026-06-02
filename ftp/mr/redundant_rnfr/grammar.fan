include("../ftp-utils.fan")

# =============================================================================
# FTP Redundant RNFR - Metamorphic Relation Test (RFC 959)
# =============================================================================
#
# MR: Multiple RNFR commands before RNTO should work - last RNFR wins
#
# Session A: Login → MKD (create dir) → RNFR → RNTO → RMD (cleanup) → Quit
# Session B: Login → MKD (create dir) → RNFR → RNFR → RNTO → RMD (cleanup) → Quit
#
# Using directories with random names ensures clean state for each test.
#
# Relation: Both should produce same response code (250)
#
# =============================================================================

<start> ::= <session_A> <ChangeConnection> <session_B>

<ChangeConnection> ::= r".*" := changeConnection()

# =============================================================================
# Session A: Normal Rename
# =============================================================================

<session_A> ::= <ServerA:ClientA:welcome> <ClientA:ServerA:user_cmd> <ServerA:ClientA:user_ok> <ClientA:ServerA:pass_cmd> <ServerA:ClientA:pass_ok> <create_dir_A> <rename_A> <cleanup_A> <ClientA:ServerA:quit_cmd> <ServerA:ClientA:quit_ok>

# Create directory
<create_dir_A> ::= <ClientA:ServerA:mkd_A> <ServerA:ClientA:mkd_ok_A>
<mkd_A> ::= "MKD " <dir_name_A> "\r\n"
<mkd_ok_A> ::= "257 " <text> "\r\n"

# Normal rename: single RNFR → RNTO → LIST to verify
<rename_A> ::= <ClientA:ServerA:rnfr_A> <ServerA:ClientA:rnfr_ok_A> <ClientA:ServerA:rnto_A> <ServerA:ClientA:rnto_response_A> <verify_list_A>
<rnfr_A> ::= "RNFR " <dir_name_A> "\r\n"
<rnfr_ok_A> ::= "350 " <text> "\r\n"
<rnto_A> ::= "RNTO " <target_name_A> "\r\n"
<rnto_response_A> ::= r"[0-9]{3} " <text> "\r\n"

# Verify rename with LIST command (requires EPSV + data connection)
<verify_list_A> ::= <epsv_setup_A> <list_exchange_A>

# Enter extended passive mode and get data port
<epsv_setup_A> ::= <ClientA:ServerA:epsv_cmd_A> <ServerA:ClientA:epsv_response_A>
<epsv_cmd_A> ::= "EPSV\r\n"
<epsv_response_A> ::= "229 Entering extended passive mode (|||" <open_port_A> "|).\r\n"
<open_port_A> ::= <passive_port_A> := open_data_port_A(int(<open_port_param_A>))
<open_port_param_A> ::= <passive_port_A> := open_data_port_A(int(<open_port_A>))
<passive_port_A> ::= r"[1-9][0-9]{0,4}" := 50100

# Send LIST, receive data on data connection, get completion status
<list_exchange_A> ::= <ClientA:ServerA:list_cmd_A> <list_transfer_A>
<list_cmd_A> ::= "LIST\r\n"
<list_transfer_A> ::= <ServerDataA:ClientDataA:list_data_A> <SocketControlServerA:close_data_A> <ServerA:ClientA:list_status_A>
<list_data_A> ::= r"[\s\S]+"
<close_data_A> ::= "Data socket closed.\r\n"
<list_status_A> ::= r"[0-9]{3} " <text> "\r\n" (r"[0-9]{3} " <text> "\r\n")?

# Cleanup: remove renamed directory
<cleanup_A> ::= <ClientA:ServerA:rmd_A> <ServerA:ClientA:rmd_ok_A>
<rmd_A> ::= "RMD " <target_name_A> "\r\n"
<rmd_ok_A> ::= "250 " <text> "\r\n"

# =============================================================================
# Session B: Redundant RNFR
# =============================================================================

<session_B> ::= <ServerB:ClientB:welcome> <ClientB:ServerB:user_cmd> <ServerB:ClientB:user_ok> <ClientB:ServerB:pass_cmd> <ServerB:ClientB:pass_ok> <create_dir_B> <redundant_rename_B> <cleanup_B> <ClientB:ServerB:quit_cmd> <ServerB:ClientB:quit_ok>

# Create directory
<create_dir_B> ::= <ClientB:ServerB:mkd_B> <ServerB:ClientB:mkd_ok_B>
<mkd_B> ::= "MKD " <dir_name_B> "\r\n"
<mkd_ok_B> ::= "257 " <text> "\r\n"

# Redundant RNFR: multiple RNFR → single RNTO → LIST to verify
<redundant_rename_B> ::= <redundant_rnfr_path> <ClientB:ServerB:rnto_B> <ServerB:ClientB:rnto_response_B> <verify_list_B>

<redundant_rnfr_path> ::= <double_rnfr> | <triple_rnfr>

# Path 1: Double RNFR
<double_rnfr> ::= <ClientB:ServerB:rnfr_B> <ServerB:ClientB:rnfr_response_B> <ClientB:ServerB:rnfr_B> <ServerB:ClientB:rnfr_response_B>

# Path 2: Triple RNFR
<triple_rnfr> ::= <ClientB:ServerB:rnfr_B> <ServerB:ClientB:rnfr_response_B> <ClientB:ServerB:rnfr_B> <ServerB:ClientB:rnfr_response_B> <ClientB:ServerB:rnfr_B> <ServerB:ClientB:rnfr_response_B>

<rnfr_B> ::= "RNFR " <dir_name_B> "\r\n"
<rnfr_response_B> ::= r"[0-9]{3} " <text> "\r\n"
<rnto_B> ::= "RNTO " <target_name_B> "\r\n"
<rnto_response_B> ::= r"[0-9]{3} " <text> "\r\n"

# Verify rename with LIST command (requires EPSV + data connection)
<verify_list_B> ::= <epsv_setup_B> <list_exchange_B>

# Enter extended passive mode and get data port
<epsv_setup_B> ::= <ClientB:ServerB:epsv_cmd_B> <ServerB:ClientB:epsv_response_B>
<epsv_cmd_B> ::= "EPSV\r\n"
<epsv_response_B> ::= "229 Entering extended passive mode (|||" <open_port_B> "|).\r\n"
<open_port_B> ::= <passive_port_B> := open_data_port_B(int(<open_port_param_B>))
<open_port_param_B> ::= <passive_port_B> := open_data_port_B(int(<open_port_B>))
<passive_port_B> ::= r"[1-9][0-9]{0,4}" := 50101

# Send LIST, receive data on data connection, get completion status
<list_exchange_B> ::= <ClientB:ServerB:list_cmd_B> <list_transfer_B>
<list_cmd_B> ::= "LIST\r\n"
<list_transfer_B> ::= <ServerDataB:ClientDataB:list_data_B> <SocketControlServerB:close_data_B> <ServerB:ClientB:list_status_B>
<list_data_B> ::= r"[\s\S]+"
<close_data_B> ::= "Data socket closed.\r\n"
<list_status_B> ::= r"[0-9]{3} " <text> "\r\n" (r"[0-9]{3} " <text> "\r\n")?

# Cleanup: remove renamed directory
<cleanup_B> ::= <ClientB:ServerB:rmd_B> <ServerB:ClientB:rmd_ok_B>
<rmd_B> ::= "RMD " <target_name_B> "\r\n"
<rmd_ok_B> ::= "250 " <text> "\r\n"

# =============================================================================
# Directory Names (fixed per session to ensure consistency)
# =============================================================================

<dir_name_A> ::= "testdir_a"
<target_name_A> ::= "renamed_a"

<dir_name_B> ::= "testdir_b"
<target_name_B> ::= "renamed_b"

# =============================================================================
# Shared
# =============================================================================

<welcome>  ::= "220 " r".*" "\r\n"
<user_cmd> ::= "USER user\r\n"
<user_ok>  ::= "331 " <text> "\r\n"
<pass_cmd> ::= "PASS 12345\r\n"
<pass_ok>  ::= "230 " <text> "\r\n"
<quit_cmd> ::= "QUIT\r\n"
<quit_ok>  ::= "221 " <text> "\r\n"

<text> ::= r'[\x20-\x7E]+'

# =============================================================================
# Metamorphic Constraint
# =============================================================================

where validateRename(<rnto_response_A>, <rnto_response_B>, <list_data_A>, <list_data_B>, <target_name_A>, <target_name_B>)

def validateRename(responseA, responseB, listA, listB, targetA, targetB):
    codeA = str(responseA)[:3]
    codeB = str(responseB)[:3]

    listStrA = str(listA)
    listStrB = str(listB)

    # Check RNTO response codes match
    codes_match = codeA == codeB

    # Check if renamed directories appear in LIST output
    targetA_found = str(targetA) in listStrA
    targetB_found = str(targetB) in listStrB

    # Both checks must pass
    if codes_match and targetA_found and targetB_found:
        print("[PASS] Redundant RNFR handled correctly")
        print("  RNTO codes: A=" + codeA + ", B=" + codeB)
        print("  Directory verified: A=" + str(targetA) + ", B=" + str(targetB))
    else:
        print("[VIOLATION] Redundant RNFR validation failed")
        if not codes_match:
            print("  RNTO codes differ: A=" + codeA + ", B=" + codeB)
            print("    Normal (A): " + str(responseA).strip())
            print("    Redundant (B): " + str(responseB).strip())
        if not targetA_found:
            print("  Target directory '" + str(targetA) + "' NOT found in Session A LIST")
            print("    LIST response: " + listStrA[:100])
        if not targetB_found:
            print("  Target directory '" + str(targetB) + "' NOT found in Session B LIST")
            print("    LIST response: " + listStrB[:100])

    return True
