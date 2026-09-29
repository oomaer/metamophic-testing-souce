<start> ::= <session_A> <ChangeConnection> <session_B>

<ChangeConnection> ::= r".*" := changeConnection()

<file_data> ::= "hello world"
<file_name> ::= "test_file.txt"

<session_A> ::= <ServerA:ClientA:welcome><authenication_seq_A> <set_binary_A> <store_file_A> <size_check_A> <ClientA:ServerA:quit_cmd> <ServerA:ClientA:quit_ok>
<authenication_seq_A> ::=  <ClientA:ServerA:user_cmd> <ServerA:ClientA:user_ok> <ClientA:ServerA:pass_cmd> <ServerA:ClientA:pass_ok>

<set_binary_A> ::= <ClientA:ServerA:type_cmd_A> <ServerA:ClientA:type_ok_A>
<type_cmd_A> ::= "TYPE I\r\n"
<type_ok_A> ::= "200 " <text> "\r\n"

<store_file_A> ::= <epsv_A> <stor_transfer_A>

<epsv_A> ::= <ClientA:ServerA:epsv_cmd_A> <ServerA:ClientA:epsv_response_A>
<epsv_cmd_A> ::= "EPSV\r\n"
<epsv_response_A> ::= "229 Entering extended passive mode (|||" <open_port_A_dynamic> "|).\r\n"
<open_port_A_dynamic> ::= <passive_port_A> := open_data_port_A(int(<open_port_param_A>))
<open_port_param_A> ::= <passive_port_A> := open_data_port_A(int(<open_port_A_dynamic>))
<passive_port_A> ::= r"[1-9][0-9]{0,4}" := 50100

<stor_transfer_A> ::= <ClientA:ServerA:stor_cmd_A> <ServerA:ClientA:stor_ready_A> <ClientDataA:ServerDataA:file_data_A> <SocketControlClientA:close_data_A> <ServerA:ClientA:stor_complete_A>

<stor_cmd_A> ::= "STOR " <file_name> "\r\n"
<stor_ready_A> ::= r"1[0-9]{2}" " " <text> "\r\n"
<file_data_A> ::= <file_data>
<close_data_A> ::= "Data socket closed.\r\n"
<stor_complete_A> ::= r"2[0-9]{2}" " " <text> "\r\n"

<size_check_A> ::= <ClientA:ServerA:size_cmd_A> <ServerA:ClientA:size_response_A>
<size_cmd_A> ::= "SIZE " <file_name> "\r\n"
<size_response_A> ::= r"[0-9]{3}" " " <size_value_A> "\r\n"
<size_value_A> ::= r"[0-9]+"

<session_B> ::= <ServerB:ClientB:welcome> <authentication_seq_B><set_binary_B> <store_file_B> <append_sequence_B> <size_after_B> <ClientB:ServerB:quit_cmd> <ServerB:ClientB:quit_ok>

<authentication_seq_B> ::= <ClientB:ServerB:user_cmd> <ServerB:ClientB:user_ok> <ClientB:ServerB:pass_cmd> <ServerB:ClientB:pass_ok> 
<set_binary_B> ::= <ClientB:ServerB:type_cmd_B> <ServerB:ClientB:type_ok_B>
<type_cmd_B> ::= "TYPE I\r\n"
<type_ok_B> ::= "200 " <text> "\r\n"

<store_file_B> ::= <epsv_B> <stor_transfer_B>

<stor_transfer_B> ::= <ClientB:ServerB:stor_cmd_B> <ServerB:ClientB:stor_ready_B> <ClientDataB:ServerDataB:file_data_B> <SocketControlClientB:close_data> <ServerB:ClientB:stor_complete_B>

<stor_cmd_B> ::= "STOR " <file_name> "\r\n"
<stor_ready_B> ::= r"1[0-9]{2}" " " <text> "\r\n"
<file_data_B> ::= <file_data>
<stor_complete_B> ::= r"2[0-9]{2}" " " <text> "\r\n"

<append_sequence_B> ::= <single_append> | <double_append> | <triple_append>

<single_append> ::= <append_with_data_1>

<double_append> ::= <append_with_data_1> <append_with_data_2>

<triple_append> ::= <append_with_data_1> <append_with_data_2> <append_with_data_3>

<append_with_data_1> ::= <epsv_B> <appe_transfer_1>
<append_with_data_2> ::= <epsv_B> <appe_transfer_2>
<append_with_data_3> ::= <epsv_B> <appe_transfer_3>

<epsv_B> ::= <ClientB:ServerB:epsv_cmd> <ServerB:ClientB:epsv_response>
<epsv_cmd> ::= "EPSV\r\n"
<epsv_response> ::= "229 Entering extended passive mode (|||" <open_port_B_dynamic> "|).\r\n"
<open_port_B_dynamic> ::= <passive_port_B> := open_data_port_B(int(<open_port_param_B>))
<open_port_param_B> ::= <passive_port_B> := open_data_port_B(int(<open_port_B_dynamic>))
<passive_port_B> ::= r"[1-9][0-9]{0,4}" := 50101

<appe_transfer_1> ::= <ClientB:ServerB:appe_cmd> <ServerB:ClientB:appe_start> <ClientDataB:ServerDataB:append_data_1> <SocketControlClientB:close_data> <ServerB:ClientB:appe_done>
<appe_transfer_2> ::= <ClientB:ServerB:appe_cmd> <ServerB:ClientB:appe_start> <ClientDataB:ServerDataB:append_data_2> <SocketControlClientB:close_data> <ServerB:ClientB:appe_done>
<appe_transfer_3> ::= <ClientB:ServerB:appe_cmd> <ServerB:ClientB:appe_start> <ClientDataB:ServerDataB:append_data_3> <SocketControlClientB:close_data> <ServerB:ClientB:appe_done>

<appe_cmd> ::= "APPE " <file_name> "\r\n"
<appe_start> ::= r"1[0-9]{2}" " " <text> "\r\n"
<append_data_1> ::= r"[A-Za-z0-9]{10,50}"
<append_data_2> ::= r"[A-Za-z0-9]{20,100}"
<append_data_3> ::= r"[A-Za-z0-9]{30,150}"
<close_data> ::= "Data socket closed.\r\n"
<appe_done> ::= r"2[0-9]{2}" " " <text> "\r\n"

<size_after_B> ::= <ClientB:ServerB:size_cmd_after> <ServerB:ClientB:size_response_after>
<size_cmd_after> ::= "SIZE " <file_name> "\r\n"
<size_response_after> ::= r"[0-9]{3}" " " <size_value_after> "\r\n"
<size_value_after> ::= r"[0-9]+"
<welcome>  ::= "220 " r".*" "\r\n"
<user_cmd> ::= "USER user\r\n"
<user_ok>  ::= "331 " <text> "\r\n"
<pass_cmd> ::= "PASS 12345\r\n"
<pass_ok>  ::= "230 " <text> "\r\n"
<quit_cmd> ::= "QUIT\r\n"
<quit_ok>  ::= "221 " <text> "\r\n"

<text> ::= r'[\x20-\x7E]+'

where validateSizeAfterAPPE(<size_value_A>, <size_value_after>, <append_data_1>, <append_data_2>, <append_data_3>)