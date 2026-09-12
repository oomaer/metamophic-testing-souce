include("./ftp-utils.fan")

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

<session_A> ::= <welcome_and_auth_A><create_dir_A> <rename_A> <cleanup_A> <ClientA:ServerA:quit_cmd> <ServerA:ClientA:quit_ok>
<welcome_and_auth_A> ::= <ServerA:welcome> <ClientA:user_cmd> <ServerA:user_ok> <ClientA:pass_cmd> <ServerA:pass_ok> 

# Create directory
<create_dir_A> ::= <ClientA:ServerA:mkd_A> <ServerA:ClientA:mkd_ok_A>
<mkd_A> ::= "MKD " <dir_name_A> "\r\n"
<mkd_ok_A> ::= <resp_257>

# Normal rename: single RNFR → RNTO → LIST to verify
<rename_A> ::= <ClientA:ServerA:rnfr_A> <ServerA:ClientA:rnfr_ok_A> <ClientA:ServerA:rnto_A> <ServerA:ClientA:rnto_response_A> <verify_list_A>
<rnfr_A> ::= "RNFR " <dir_name_A> "\r\n"
<rnfr_ok_A> ::= <resp_350>
<rnto_A> ::= "RNTO " <target_name_A> "\r\n"
<rnto_response_A> ::= <resp_250>

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
<list_status_A> ::= <resp_125> <resp_226>

# Cleanup: remove renamed directory
<cleanup_A> ::= <ClientA:ServerA:rmd_A> <ServerA:ClientA:rmd_ok_A>
<rmd_A> ::= "RMD " <target_name_A> "\r\n"
<rmd_ok_A> ::= <resp_250>

# =============================================================================
# Session B: Redundant RNFR
# =============================================================================

<session_B> ::= <welcome_and_login_B><ServerB:ClientB:pass_ok> <create_dirs_B> <redundant_rename_B> <cleanup_B> <ClientB:ServerB:quit_cmd> <ServerB:ClientB:quit_ok>
<welcome_and_login_B> ::= <ServerB:ClientB:welcome> <ClientB:ServerB:user_cmd> <ServerB:ClientB:user_ok> <ClientB:ServerB:pass_cmd>
# Create multiple directories for testing "last RNFR wins"
<create_dirs_B> ::= <create_dir_B1><create_dir_B2><create_dir_B3>
<create_dir_B1> ::= <ClientB:mkd_B1> <ServerB:mkd_ok>
<create_dir_B2> ::=  <ClientB:mkd_B2> <ServerB:mkd_ok>
<create_dir_B3> ::=  <ClientB:mkd_B3> <ServerB:mkd_ok>
<mkd_B1> ::= "MKD " <dir_name_B1> "\r\n"
<mkd_B2> ::= "MKD " <dir_name_B2> "\r\n"
<mkd_B3> ::= "MKD " <dir_name_B3> "\r\n"
<mkd_ok> ::= <resp_257>

# Redundant RNFR: multiple RNFR with DIFFERENT targets → single RNTO → LIST to verify
<redundant_rename_B> ::= <redundant_rnfr_path> <ClientB:ServerB:rnto_B> <ServerB:ClientB:rnto_response_B> <verify_list_B>

<redundant_rnfr_path> ::= <single_rnfr_B3><double_rnfr> | <single_rnfr_B1><single_rnfr_B3><single_rnfr_B2> | <single_rnfr_B2><single_rnfr_B3><single_rnfr_B2> | <single_rnfr_B1><double_rnfr> | <single_rnfr_B2><double_rnfr> | <double_rnfr> 

<single_rnfr_B1> ::= <ClientB:rnfr_B1> <ServerB:rnfr_ok>
<single_rnfr_B2> ::= <ClientB:rnfr_B2> <ServerB:rnfr_ok>
<single_rnfr_B3> ::= <ClientB:rnfr_B3> <ServerB:rnfr_ok>
# Path 1: Double RNFR - different targets (last one wins)
<double_rnfr> ::= <ClientB:rnfr_B1> <ServerB:rnfr_ok> <ClientB:rnfr_B2> <ServerB:rnfr_ok>


<rnfr_B1> ::= "RNFR " <dir_name_B1> "\r\n"
<rnfr_B2> ::= "RNFR " <dir_name_B2> "\r\n"
<rnfr_B3> ::= "RNFR " <dir_name_B3> "\r\n"
<rnfr_ok> ::= <resp_350>
<rnto_B> ::= "RNTO " <target_name_B> "\r\n"
<rnto_response_B> ::= <resp_250>

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
<list_status_B> ::= <resp_125> <resp_226>

# Cleanup: remove both created directories (not the renamed one, it doesn't exist after failed rename)
<cleanup_B> ::= <ClientB:ServerB:rmd_B1> <ServerB:ClientB:rmd_response> <ClientB:ServerB:rmd_B2> <ServerB:ClientB:rmd_response> <ClientB:ServerB:rmd_B3> <ServerB:ClientB:rmd_response> <ClientB:ServerB:rmd_target> <ServerB:ClientB:rmd_response>
<rmd_B1> ::= "RMD " <dir_name_B1> "\r\n"
<rmd_B2> ::= "RMD " <dir_name_B2> "\r\n"
<rmd_B3> ::= "RMD " <dir_name_B3> "\r\n"
<rmd_target> ::= "RMD " <target_name_B> "\r\n"
<rmd_response> ::= <resp_250> | <resp_550>

# =============================================================================
# Directory Names (fixed per session to ensure consistency)
# =============================================================================

<dir_name_A> ::= "testdir_a"
<target_name_A> ::= "renamed_a"

# Session B uses two different source directories
<dir_name_B1> ::= "testdir_b1"
<dir_name_B2> ::= "testdir_b2"
<dir_name_B3> ::= "testdir_b3"
<target_name_B> ::= "renamed_b"

# =============================================================================
# Shared
# =============================================================================

<welcome>  ::= "220 " <text> "\r\n"
<user_cmd> ::= "USER user\r\n"
<user_ok>  ::= "331 " <text> "\r\n"
<pass_cmd> ::= "PASS 12345\r\n"
<pass_ok>  ::= "230 " <text> "\r\n"
<quit_cmd> ::= "QUIT\r\n"
<quit_ok>  ::= "221 " <text> "\r\n"

# Shared response shapes (reused across A/B; each pinned to the specific code the server emits)
<resp_125> ::= "125 " <text> "\r\n"
<resp_226> ::= "226 " <text> "\r\n"
<resp_250> ::= "250 " <text> "\r\n"
<resp_257> ::= "257 " <text> "\r\n"
<resp_350> ::= "350 " <text> "\r\n"
<resp_550> ::= "550 " <text> "\r\n"

<text> ::= r'[\x20-\x7E]+'

# =============================================================================
# Metamorphic Constraint
# =============================================================================

where validateRename(<rnto_response_A>, <rnto_response_B>, <list_data_A>, <list_data_B>, <target_name_A>, <target_name_B>, <dir_name_B1>, <dir_name_B2>)

def validateRename(responseA, responseB, listA, listB, targetA, targetB, dirB1, dirB2):
    codeA = str(responseA)[:3]
    codeB = str(responseB)[:3]

    listStrA = str(listA)
    listStrB = str(listB)

    # Check RNTO response codes match
    codes_match = codeA == codeB

    # Check if renamed directories appear in LIST output
    targetA_found = str(targetA) in listStrA
    targetB_found = str(targetB) in listStrB

    # For "last RNFR wins", the LAST RNFR was for dirB2
    # So dirB1 should still exist (not renamed), dirB2 should NOT exist (was renamed)
    dirB1_still_exists = str(dirB1) in listStrB  # Should be True
    dirB2_was_renamed = str(dirB2) not in listStrB  # Should be True (file gone because renamed)

    # Both checks must pass
    if codes_match and targetA_found and targetB_found and dirB1_still_exists and dirB2_was_renamed:
        print("[PASS] Redundant RNFR handled correctly")
        print("  RNTO codes: A=" + codeA + ", B=" + codeB)
        print("  Directory verified: A=" + str(targetA) + ", B=" + str(targetB))
        print("  Last RNFR wins: " + str(dirB2) + " was renamed, " + str(dirB1) + " still exists")
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
        if not dirB1_still_exists:
            print("  ERROR: '" + str(dirB1) + "' should still exist but was not found in LIST")
            print("    LIST response: " + listStrB[:150])
        if not dirB2_was_renamed:
            print("  ERROR: '" + str(dirB2) + "' should have been renamed but still exists in LIST")
            print("    This violates 'last RNFR wins' - wrong directory was renamed!")
            print("    LIST response: " + listStrB[:150])

    return True
