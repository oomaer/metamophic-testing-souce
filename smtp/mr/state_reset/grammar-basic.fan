<start> ::= <Interation1> <ChangeConnection> <Interation2>
<Interation1> ::= <ServerA:response_setup><ClientA:request_ehlo><ServerA:response_ehlo><state_logged_out_A>
<Interation2> ::= <ServerB:response_setup><ClientB:request_ehlo><ServerB:response_ehlo><state_logged_out_B>
<ChangeConnection> ::= r".*" := changeConnection()
<state_logged_out_A> ::= <exchange_login_valid_A>
<state_logged_out_B> ::= <exchange_login_valid_B>
<state_logged_in_A> ::= <exchange_send_email_A><exchange_quit_A>
<state_logged_in_B> ::= <reset_path_B><exchange_send_email_B><exchange_quit_B>
<exchange_login_valid_A> ::= <ClientA:request_auth><ServerA:response_auth_expect_user><ClientA:request_auth_user><ServerA:response_auth_expect_pass><ClientA:request_auth_pass><ServerA:response_auth_success><state_logged_in_A>
<exchange_send_email_A> ::= <ClientA:request_mail_from><ServerA:response_mail_from><ClientA:request_rcpt_to><ServerA:response_rcpt_to><ClientA:request_data><ServerA:response_data><ClientA:email_content><ServerA:response_emailA_sent>
<exchange_quit_A> ::= <ClientA:request_quit><ServerA:response_quit>
<exchange_login_valid_B> ::= <ClientB:request_auth><ServerB:response_auth_expect_user><ClientB:request_auth_user><ServerB:response_auth_expect_pass><ClientB:request_auth_pass><ServerB:response_auth_success><state_logged_in_B>
<reset_path_B> ::= <reset_after_mail_from_B> | <reset_after_rcpt_to_B> | <reset_after_invalid_mail_from_B> | <reset_after_invalid_rcpt_to_B>
<reset_after_mail_from_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><exchange_reset_B>
<reset_after_rcpt_to_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><ClientB:request_rcpt_to><ServerB:response_rcpt_to><exchange_reset_B>
<reset_after_invalid_mail_from_B> ::= <ClientB:request_invalid_mail_from><ServerB:response_invalid_mail_from><exchange_reset_B>
<reset_after_invalid_rcpt_to_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><ClientB:request_invalid_rcpt_to><ServerB:response_invalid_rcpt_to><exchange_reset_B>
<exchange_reset_B> ::= <ClientB:request_rset><ServerB:response_rset>
<exchange_send_email_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from_B><ClientB:request_rcpt_to><ServerB:response_rcpt_to_B><ClientB:request_data><ServerB:response_data_B><ClientB:email_content><ServerB:response_emailB_sent>
<exchange_quit_B> ::= <ClientB:request_quit><ServerB:response_quit>
<request_ehlo> ::= 'EHLO localhost\r\n'
<response_ehlo> ::= ("250-" r"."+ "\r\n")+ "250 " r"."+ "\r\n"
<response_setup> ::= "220 " r"."+ "\r\n"
<request_auth> ::= 'AUTH LOGIN\r\n'
<response_auth_expect_user> ::= "334 " r"[A-Za-z0-9+/=]+" "\r\n"
<request_auth_user> ::= 'dGhlX3VzZXI=\r\n'
<response_auth_expect_pass> ::= "334 " r"[A-Za-z0-9+/=]+" "\r\n"
<request_auth_pass> ::= 'dGhlX3Bhc3N3b3Jk\r\n'
<response_auth_success> ::= "235 " r"."+ "\r\n"
<request_mail_from> ::= 'MAIL FROM:<sender@example.com>\r\n'
<response_mail_from> ::= "250 " r"."+ "\r\n"
<response_mail_from_B> ::= r"[2-5][0-9]{2}" " " r"."+ "\r\n"
<request_rcpt_to> ::= 'RCPT TO:<recipient@example.com>\r\n'
<response_rcpt_to> ::= "250 " r"."+ "\r\n"
<response_rcpt_to_B> ::= r"[2-5][0-9]{2}" " " r"."+ "\r\n"
<request_invalid_mail_from> ::= 'MAIL FROM:<invalid@>\r\n'
<response_invalid_mail_from> ::= r"[45][0-9]{2}" " " r"."+ "\r\n"
<request_invalid_rcpt_to> ::= 'RCPT TO:<invalid@>\r\n'
<response_invalid_rcpt_to> ::= r"[45][0-9]{2}" " " r"."+ "\r\n"
<request_data> ::= 'DATA\r\n'
<response_data> ::= "354 " r"."+ "\r\n"
<response_data_B> ::= r"[2-5][0-9]{2}" " " r"."+ "\r\n"
<email_content> ::= 'Subject: Test Email\r\n\r\nThis is a test email.\r\n.\r\n'
<response_emailA_sent> ::= "250 " r"."+ "\r\n"
<response_emailB_sent> ::= r"[2-5][0-9]{2}" " " r"."+ "\r\n"
<request_rset> ::= 'RSET\r\n'
<response_rset> ::= "250 " r"."+ "\r\n"
<request_quit> ::= 'QUIT\r\n'
<response_quit> ::= "221 " r"."+ "\r\n"
where validateResponses(<response_emailA_sent>, <response_emailB_sent>)
where validateMailFrom(<response_mail_from>, <response_mail_from_B>)
