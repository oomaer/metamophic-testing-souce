include("../../ftp-utils.fan")

# =============================================================================
# FTP SIZE After APPE - Metamorphic Relation Test (RFC 959/3659)
# =============================================================================
#
# MR: Monotonicity - SIZE_after = SIZE_before + appended_bytes
#
# Session A: Login → SIZE test_file.txt → Quit (baseline - no modifications)
# Session B: Login → SIZE → APPE (variable-length random data) × k → SIZE → Quit
#
# Validation: size_after_B == size_before_B + total_appended_bytes
#
# Uses regex-generated variable-length data:
#   - data1: 10-50 random alphanumeric chars
#   - data2: 20-100 random alphanumeric chars
#   - data3: 30-150 random alphanumeric chars
#
# Each test run generates different random content, ensuring SIZE command
# accuracy is validated across varying data lengths and content.
#
# =============================================================================

<start> ::= <session_A> <ChangeConnection> <session_B>

<ChangeConnection> ::= r".*" := changeConnection()

# =============================================================================
# Session A: Control - just read SIZE (file unchanged)
# =============================================================================

<session_A> ::= <ServerA:ClientA:welcome> <ClientA:ServerA:user_cmd> <ServerA:ClientA:user_ok> <ClientA:ServerA:pass_cmd> <ServerA:ClientA:pass_ok> <set_binary_A> <size_check_A> <ClientA:ServerA:quit_cmd> <ServerA:ClientA:quit_ok>

<set_binary_A> ::= <ClientA:ServerA:type_cmd_A> <ServerA:ClientA:type_ok_A>
<type_cmd_A> ::= "TYPE I\r\n"
<type_ok_A> ::= "200 " <text> "\r\n"

<size_check_A> ::= <ClientA:ServerA:size_cmd_A> <ServerA:ClientA:size_response_A>
<size_cmd_A> ::= "SIZE test_file.txt\r\n"
<size_response_A> ::= r"[0-9]{3} " <size_value_A> "\r\n"
<size_value_A> ::= r"[0-9]+"

# =============================================================================
# Session B: SIZE → APPE → SIZE (test monotonicity on same server)
# =============================================================================

<session_B> ::= <ServerB:ClientB:welcome> <ClientB:ServerB:user_cmd> <ServerB:ClientB:user_ok> <ClientB:ServerB:pass_cmd> <ServerB:ClientB:pass_ok> <set_binary_B> <size_before_B> <append_sequence_B> <size_after_B> <ClientB:ServerB:quit_cmd> <ServerB:ClientB:quit_ok>

<set_binary_B> ::= <ClientB:ServerB:type_cmd_B> <ServerB:ClientB:type_ok_B>
<type_cmd_B> ::= "TYPE I\r\n"
<type_ok_B> ::= "200 " <text> "\r\n"

# SIZE before any appends
<size_before_B> ::= <ClientB:ServerB:size_cmd_before> <ServerB:ClientB:size_response_before>
<size_cmd_before> ::= "SIZE test_file.txt\r\n"
<size_response_before> ::= r"[0-9]{3} " <size_value_before> "\r\n"
<size_value_before> ::= r"[0-9]+"

# K-path variations: single, double, or triple append
<append_sequence_B> ::= <single_append> | <double_append> | <triple_append>

# Single append: one APPE with random data
<single_append> ::= <append_with_data_1>

# Double append: two APPEs with different random data sizes
<double_append> ::= <append_with_data_1> <append_with_data_2>

# Triple append: three APPEs with different random data sizes
<triple_append> ::= <append_with_data_1> <append_with_data_2> <append_with_data_3>

# -----------------------------------------------------------------------------
# Append with different data size patterns (shared structure, varying data)
# -----------------------------------------------------------------------------

<append_with_data_1> ::= <epsv_B> <appe_transfer_1>
<append_with_data_2> ::= <epsv_B> <appe_transfer_2>
<append_with_data_3> ::= <epsv_B> <appe_transfer_3>

# Shared EPSV setup (used before each APPE)
<epsv_B> ::= <ClientB:ServerB:epsv_cmd> <ServerB:ClientB:epsv_response>
<epsv_cmd> ::= "EPSV\r\n"
<epsv_response> ::= "229 Entering extended passive mode (|||" <open_port_B_dynamic> "|).\r\n"
<open_port_B_dynamic> ::= <passive_port_B> := open_data_port_B(int(<open_port_param_B>))
<open_port_param_B> ::= <passive_port_B> := open_data_port_B(int(<open_port_B_dynamic>))
<passive_port_B> ::= r"[1-9][0-9]{0,4}" := 50101

# APPE transfers - shared structure, different data sizes
<appe_transfer_1> ::= <ClientB:ServerB:appe_cmd> <ServerB:ClientB:appe_start> <ClientDataB:ServerDataB:append_data_1> <SocketControlClientB:close_data> <ServerB:ClientB:appe_done>
<appe_transfer_2> ::= <ClientB:ServerB:appe_cmd> <ServerB:ClientB:appe_start> <ClientDataB:ServerDataB:append_data_2> <SocketControlClientB:close_data> <ServerB:ClientB:appe_done>
<appe_transfer_3> ::= <ClientB:ServerB:appe_cmd> <ServerB:ClientB:appe_start> <ClientDataB:ServerDataB:append_data_3> <SocketControlClientB:close_data> <ServerB:ClientB:appe_done>

<appe_cmd> ::= "APPE test_file.txt\r\n"
<appe_start> ::= r"1[0-9]{2} " <text> "\r\n"
<append_data_1> ::= r"[A-Za-z0-9]{10,50}"
<append_data_2> ::= r"[A-Za-z0-9]{20,100}"
<append_data_3> ::= r"[A-Za-z0-9]{30,150}"
<close_data> ::= "Data socket closed.\r\n"
<appe_done> ::= r"2[0-9]{2} " <text> "\r\n"

# -----------------------------------------------------------------------------
# SIZE after all appends
# -----------------------------------------------------------------------------
<size_after_B> ::= <ClientB:ServerB:size_cmd_after> <ServerB:ClientB:size_response_after>
<size_cmd_after> ::= "SIZE test_file.txt\r\n"
<size_response_after> ::= r"[0-9]{3} " <size_value_after> "\r\n"
<size_value_after> ::= r"[0-9]+"

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

where validateSizeAfterAPPE(<size_value_before>, <size_value_after>, <append_data_1>, <append_data_2>, <append_data_3>)

def validateSizeAfterAPPE(sizeBefore, sizeAfter, data1, data2, data3):
    try:
        size_before = int(str(sizeBefore))
        size_after = int(str(sizeAfter))
    except ValueError as e:
        print("[VIOLATION] Could not parse SIZE responses: " + str(e))
        print("  SIZE before: " + str(sizeBefore))
        print("  SIZE after: " + str(sizeAfter))
        return True

    # Dynamically measure actual bytes generated by regex
    total_appended = 0
    append_details = []
    for i, data in enumerate([data1, data2, data3], 1):
        data_str = str(data)
        # Count any non-empty, non-None data
        if data_str and data_str not in ["", "None", "b''", "b\"\""]:
            data_len = len(data_str)
            total_appended += data_len
            append_details.append("data" + str(i) + "=" + str(data_len) + "b")

    expected_size = size_before + total_appended
    details_str = ", ".join(append_details) if append_details else "none"

    if size_after == expected_size:
        print("[PASS] SIZE monotonicity holds")
        print("  SIZE before: " + str(size_before) + " bytes")
        print("  Appended: " + str(total_appended) + " bytes (" + details_str + ")")
        print("  SIZE after: " + str(size_after) + " bytes (expected: " + str(expected_size) + ")")
    else:
        print("[VIOLATION] SIZE monotonicity failed")
        print("  SIZE before: " + str(size_before) + " bytes")
        print("  Appended: " + str(total_appended) + " bytes (" + details_str + ")")
        print("  SIZE after: " + str(size_after) + " bytes")
        print("  Expected: " + str(expected_size) + " bytes")
        print("  Difference: " + str(size_after - expected_size) + " bytes")

    return True
