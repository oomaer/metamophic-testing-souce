include("../../ftp-utils.fan")

# =============================================================================
# FTP SIZE After APPE - Metamorphic Relation Test (RFC 959/3659)
# =============================================================================
#
# MR: Monotonicity - SIZE_after = SIZE_before + appended_bytes
#
# Session A: Login → SIZE test_file.txt → Quit (baseline - no modifications)
# Session B: Login → SIZE → APPE (N bytes) × k → SIZE → Quit
#
# Validation: size_after_B == size_before_B + appended_bytes
#
# Server A is the control (unmodified file), Server B performs the append test.
# Each test case checks that SIZE accurately reflects APPE operations.
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

# Single append: 10 bytes
<single_append> ::= <append_operation_1>

# Double append: 10 + 20 = 30 bytes total
<double_append> ::= <append_operation_1> <append_operation_2>

# Triple append: 10 + 20 + 30 = 60 bytes total
<triple_append> ::= <append_operation_1> <append_operation_2> <append_operation_3>

# -----------------------------------------------------------------------------
# Append Operation 1: 10 bytes
# -----------------------------------------------------------------------------
<append_operation_1> ::= <epsv_setup_1> <appe_transfer_1>

<epsv_setup_1> ::= <ClientB:ServerB:epsv_cmd_1> <ServerB:ClientB:epsv_response_1>
<epsv_cmd_1> ::= "EPSV\r\n"
<epsv_response_1> ::= "229 Entering extended passive mode (|||" <open_port_1> "|).\r\n"
<open_port_1> ::= <passive_port_1> := open_data_port_B(int(<open_port_param_1>))
<open_port_param_1> ::= <passive_port_1> := open_data_port_B(int(<open_port_1>))
<passive_port_1> ::= r"[1-9][0-9]{0,4}" := 50101

<appe_transfer_1> ::= <ClientB:ServerB:appe_cmd_1> <ServerB:ClientB:appe_start_1> <ClientDataB:ServerDataB:append_data_1> <SocketControlClientB:close_data_1> <ServerB:ClientB:appe_done_1>
<appe_cmd_1> ::= "APPE test_file.txt\r\n"
<appe_start_1> ::= r"1[0-9]{2} " <text> "\r\n"
<append_data_1> ::= "AAAAAAAAAA"
<close_data_1> ::= "Data socket closed.\r\n"
<appe_done_1> ::= r"2[0-9]{2} " <text> "\r\n"

# -----------------------------------------------------------------------------
# Append Operation 2: 20 bytes
# -----------------------------------------------------------------------------
<append_operation_2> ::= <epsv_setup_2> <appe_transfer_2>

<epsv_setup_2> ::= <ClientB:ServerB:epsv_cmd_2> <ServerB:ClientB:epsv_response_2>
<epsv_cmd_2> ::= "EPSV\r\n"
<epsv_response_2> ::= "229 Entering extended passive mode (|||" <open_port_2> "|).\r\n"
<open_port_2> ::= <passive_port_2> := open_data_port_B(int(<open_port_param_2>))
<open_port_param_2> ::= <passive_port_2> := open_data_port_B(int(<open_port_2>))
<passive_port_2> ::= r"[1-9][0-9]{0,4}" := 50101

<appe_transfer_2> ::= <ClientB:ServerB:appe_cmd_2> <ServerB:ClientB:appe_start_2> <ClientDataB:ServerDataB:append_data_2> <SocketControlClientB:close_data_2> <ServerB:ClientB:appe_done_2>
<appe_cmd_2> ::= "APPE test_file.txt\r\n"
<appe_start_2> ::= r"1[0-9]{2} " <text> "\r\n"
<append_data_2> ::= "BBBBBBBBBBBBBBBBBBBB"
<close_data_2> ::= "Data socket closed.\r\n"
<appe_done_2> ::= r"2[0-9]{2} " <text> "\r\n"

# -----------------------------------------------------------------------------
# Append Operation 3: 30 bytes
# -----------------------------------------------------------------------------
<append_operation_3> ::= <epsv_setup_3> <appe_transfer_3>

<epsv_setup_3> ::= <ClientB:ServerB:epsv_cmd_3> <ServerB:ClientB:epsv_response_3>
<epsv_cmd_3> ::= "EPSV\r\n"
<epsv_response_3> ::= "229 Entering extended passive mode (|||" <open_port_3> "|).\r\n"
<open_port_3> ::= <passive_port_3> := open_data_port_B(int(<open_port_param_3>))
<open_port_param_3> ::= <passive_port_3> := open_data_port_B(int(<open_port_3>))
<passive_port_3> ::= r"[1-9][0-9]{0,4}" := 50101

<appe_transfer_3> ::= <ClientB:ServerB:appe_cmd_3> <ServerB:ClientB:appe_start_3> <ClientDataB:ServerDataB:append_data_3> <SocketControlClientB:close_data_3> <ServerB:ClientB:appe_done_3>
<appe_cmd_3> ::= "APPE test_file.txt\r\n"
<appe_start_3> ::= r"1[0-9]{2} " <text> "\r\n"
<append_data_3> ::= "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
<close_data_3> ::= "Data socket closed.\r\n"
<appe_done_3> ::= r"2[0-9]{2} " <text> "\r\n"

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

    # Calculate total appended bytes - only count non-empty, actual data
    total_appended = 0
    append_details = []
    for i, data in enumerate([data1, data2, data3], 1):
        data_str = str(data)
        # Only count if it looks like actual appended data (our A/B/C patterns)
        if data_str and len(data_str) > 0 and data_str[0] in "ABC":
            total_appended += len(data_str)
            append_details.append("data" + str(i) + "=" + str(len(data_str)) + "b")

    expected_size = size_before + total_appended
    details_str = ", ".join(append_details)

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
