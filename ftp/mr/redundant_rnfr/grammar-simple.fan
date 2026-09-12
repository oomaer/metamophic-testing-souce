
<start> ::= <session_A> <ChangeConnection> <session_B>

<ChangeConnection> ::= r".*" := changeConnection()
<session_A> ::= <welcome_and_auth_A><create_dir_A> <rename_A> <cleanup_A> <ClientA:ServerA:quit_cmd> <ServerA:ClientA:quit_ok>
<welcome_and_auth_A> ::= <ServerA:welcome> <ClientA:user_cmd> <ServerA:user_ok> <ClientA:pass_cmd> <ServerA:pass_ok> 
<create_dir_A> ::= <ClientA:ServerA:mkd_A> <ServerA:ClientA:mkd_ok_A>
<mkd_A> ::= "MKD " <dir_name_A> "\r\n"
<mkd_ok_A> ::= <resp_257>

<rename_A> ::= <ClientA:ServerA:rnfr_A> <ServerA:ClientA:rnfr_ok_A> <ClientA:ServerA:rnto_A> <ServerA:ClientA:rnto_response_A> <verify_list_A>
<rnfr_A> ::= "RNFR " <dir_name_A> "\r\n"
<rnfr_ok_A> ::= <resp_350>
<rnto_A> ::= "RNTO " <target_name_A> "\r\n"
<rnto_response_A> ::= <resp_250>
<verify_list_A> ::= <epsv_setup_A> <list_exchange_A>

<epsv_setup_A> ::= <ClientA:ServerA:epsv_cmd_A> <ServerA:ClientA:epsv_response_A>
<epsv_cmd_A> ::= "EPSV\r\n"
<epsv_response_A> ::= "229 Entering extended passive mode (|||" <open_port_A> "|).\r\n"
<open_port_A> ::= <passive_port_A> := open_data_port_A(int(<open_port_param_A>))
<open_port_param_A> ::= <passive_port_A> := open_data_port_A(int(<open_port_A>))
<passive_port_A> ::= r"[1-9][0-9]{0,4}" := 50100

<list_exchange_A> ::= <ClientA:ServerA:list_cmd_A> <list_transfer_A>
<list_cmd_A> ::= "LIST\r\n"
<list_transfer_A> ::= <ServerDataA:ClientDataA:list_data_A> <SocketControlServerA:close_data_A> <ServerA:ClientA:list_status_A>
<list_data_A> ::= r"[\s\S]+"
<close_data_A> ::= "Data socket closed.\r\n"
<list_status_A> ::= <resp_125> <resp_226>

<cleanup_A> ::= <ClientA:ServerA:rmd_A> <ServerA:ClientA:rmd_ok_A>
<rmd_A> ::= "RMD " <target_name_A> "\r\n"
<rmd_ok_A> ::= <resp_250>

<session_B> ::= <welcome_and_login_B><ServerB:ClientB:pass_ok> <create_dirs_B> <redundant_rename_B> <cleanup_B> <ClientB:ServerB:quit_cmd> <ServerB:ClientB:quit_ok>
<welcome_and_login_B> ::= <ServerB:ClientB:welcome> <ClientB:ServerB:user_cmd> <ServerB:ClientB:user_ok> <ClientB:ServerB:pass_cmd>

<create_dirs_B> ::= <create_dir_B1><create_dir_B2><create_dir_B3>
<create_dir_B1> ::= <ClientB:mkd_B1> <ServerB:mkd_ok>
<create_dir_B2> ::=  <ClientB:mkd_B2> <ServerB:mkd_ok>
<create_dir_B3> ::=  <ClientB:mkd_B3> <ServerB:mkd_ok>
<mkd_B1> ::= "MKD " <dir_name_B1> "\r\n"
<mkd_B2> ::= "MKD " <dir_name_B2> "\r\n"
<mkd_B3> ::= "MKD " <dir_name_B3> "\r\n"
<mkd_ok> ::= <resp_257>


<redundant_rename_B> ::= <redundant_rnfr_path> <ClientB:ServerB:rnto_B> <ServerB:ClientB:rnto_response_B> <verify_list_B>
<redundant_rnfr_path> ::= <single_rnfr_B3><double_rnfr> | <single_rnfr_B1><single_rnfr_B3><single_rnfr_B2> | <single_rnfr_B2><single_rnfr_B3><single_rnfr_B2> | <single_rnfr_B1><double_rnfr> | <single_rnfr_B2><double_rnfr> | <double_rnfr> 
<single_rnfr_B1> ::= <ClientB:rnfr_B1> <ServerB:rnfr_ok>
<single_rnfr_B2> ::= <ClientB:rnfr_B2> <ServerB:rnfr_ok>
<single_rnfr_B3> ::= <ClientB:rnfr_B3> <ServerB:rnfr_ok>
<double_rnfr> ::= <ClientB:rnfr_B1> <ServerB:rnfr_ok> <ClientB:rnfr_B2> <ServerB:rnfr_ok>

<rnfr_B1> ::= "RNFR " <dir_name_B1> "\r\n"
<rnfr_B2> ::= "RNFR " <dir_name_B2> "\r\n"
<rnfr_B3> ::= "RNFR " <dir_name_B3> "\r\n"
<rnfr_ok> ::= <resp_350>
<rnto_B> ::= "RNTO " <target_name_B> "\r\n"
<rnto_response_B> ::= <resp_250>

<verify_list_B> ::= <epsv_setup_B> <list_exchange_B>

<epsv_setup_B> ::= <ClientB:ServerB:epsv_cmd_B> <ServerB:ClientB:epsv_response_B>
<epsv_cmd_B> ::= "EPSV\r\n"
<epsv_response_B> ::= "229 Entering extended passive mode (|||" <open_port_B> "|).\r\n"
<open_port_B> ::= <passive_port_B> := open_data_port_B(int(<open_port_param_B>))
<open_port_param_B> ::= <passive_port_B> := open_data_port_B(int(<open_port_B>))
<passive_port_B> ::= r"[1-9][0-9]{0,4}" := 50101

<list_exchange_B> ::= <ClientB:ServerB:list_cmd_B> <list_transfer_B>
<list_cmd_B> ::= "LIST\r\n"
<list_transfer_B> ::= <ServerDataB:ClientDataB:list_data_B> <SocketControlServerB:close_data_B> <ServerB:ClientB:list_status_B>
<list_data_B> ::= r"[\s\S]+"
<close_data_B> ::= "Data socket closed.\r\n"
<list_status_B> ::= <resp_125> <resp_226>

<cleanup_B> ::= <ClientB:ServerB:rmd_B1> <ServerB:ClientB:rmd_response> <ClientB:ServerB:rmd_B2> <ServerB:ClientB:rmd_response> <ClientB:ServerB:rmd_B3> <ServerB:ClientB:rmd_response> <ClientB:ServerB:rmd_target> <ServerB:ClientB:rmd_response>
<rmd_B1> ::= "RMD " <dir_name_B1> "\r\n"
<rmd_B2> ::= "RMD " <dir_name_B2> "\r\n"
<rmd_B3> ::= "RMD " <dir_name_B3> "\r\n"
<rmd_target> ::= "RMD " <target_name_B> "\r\n"
<rmd_response> ::= <resp_250> | <resp_550>

<dir_name_A> ::= "testdir_a"
<target_name_A> ::= "renamed_a"

<dir_name_B1> ::= "testdir_b1"
<dir_name_B2> ::= "testdir_b2"
<dir_name_B3> ::= "testdir_b3"
<target_name_B> ::= "renamed_b"

<welcome>  ::= "220 " <text> "\r\n"
<user_cmd> ::= "USER user\r\n"
<user_ok>  ::= "331 " <text> "\r\n"
<pass_cmd> ::= "PASS 12345\r\n"
<pass_ok>  ::= "230 " <text> "\r\n"
<quit_cmd> ::= "QUIT\r\n"
<quit_ok>  ::= "221 " <text> "\r\n"

<resp_125> ::= "125 " <text> "\r\n"
<resp_226> ::= "226 " <text> "\r\n"
<resp_250> ::= "250 " <text> "\r\n"
<resp_257> ::= "257 " <text> "\r\n"
<resp_350> ::= "350 " <text> "\r\n"
<resp_550> ::= "550 " <text> "\r\n"

<text> ::= r'[\x20-\x7E]+'

where validateRename(<rnto_response_A>, <rnto_response_B>, <list_data_A>, <list_data_B>, <target_name_A>, <target_name_B>, <dir_name_B1>, <dir_name_B2>)