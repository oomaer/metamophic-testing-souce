<start> ::= <Interation1> <ConnectionControl:ChangeConnection> <Interation2>
<Interation1> ::= <ServerA:response_setup><ClientA:request_ehlo><ServerA:response_ehlo><state_logged_out_A>
<Interation2> ::= <ServerB:response_setup><ClientB:request_ehlo><ServerB:response_ehlo><state_logged_out_B>
<ChangeConnection> ::= "start connection B"

<state_logged_out_A> ::= <exchange_login_valid_A>
<state_logged_out_B> ::= <exchange_login_valid_B>
<state_logged_in_A> ::= <exchange_send_email_A><exchange_quit_A>
<state_logged_in_B> ::= <exchange_send_email_B><exchange_quit_B>
<exchange_login_valid_A> ::= <ClientA:request_auth><ServerA:response_auth_expect_user><ClientA:request_auth_user><ServerA:response_auth_expect_pass><ClientA:request_auth_pass><ServerA:response_auth_success><state_logged_in_A>
<exchange_send_email_A> ::= <ClientA:request_mail_from><ServerA:response_mail_from><ClientA:request_rcpt_to><ServerA:response_rcpt_to><ClientA:request_data><ServerA:response_data><ClientA:email_content><ServerA:response_emailA_sent>
<exchange_quit_A> ::= <ClientA:request_quit><ServerA:response_quit>
<exchange_login_valid_B> ::= <ClientB:request_auth><ServerB:response_auth_expect_user><ClientB:request_auth_user><ServerB:response_auth_expect_pass><ClientB:request_auth_pass><ServerB:response_auth_success><state_logged_in_B>
<exchange_send_email_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><rcpt_repeated_B><ClientB:request_data><ServerB:response_data><ClientB:email_content><ServerB:response_emailB_sent>

<rcpt_repeated_B> ::= <rcpt_2x> | <rcpt_3x> | <rcpt_n>
<rcpt_n> ::= <single_rcpt_B><rcpt_n> | <single_rcpt_B>
<rcpt_2x> ::= <single_rcpt_B><single_rcpt_B>
<rcpt_3x> ::= <single_rcpt_B><single_rcpt_B><single_rcpt_B>

<single_rcpt_B> ::= <ClientB:rcpt_simple><ServerB:response_rcpt_to_repeated>
<exchange_quit_B> ::= <ClientB:request_quit><ServerB:response_quit>
<request_ehlo> ::= 'EHLO localhost\r\n'
<response_ehlo> ::= <response_ehlo_continuation>+ "250 " r"[^\r\n]+" "\r\n"
<response_ehlo_continuation> ::= "250-" r"[^\r\n]+" "\r\n"
<response_setup> ::= "220 " r"\S+" " " r"[^\r\n]+" "\r\n"

<request_auth> ::= 'AUTH LOGIN\r\n'
<response_auth_expect_user> ::= "334 " r"[A-Za-z0-9+/=]+" "\r\n"  
<request_auth_user> ::= 'dGhlX3VzZXI=\r\n'            
<response_auth_expect_pass> ::= "334 " r"[A-Za-z0-9+/=]+" "\r\n" 
<request_auth_pass> ::= 'dGhlX3Bhc3N3b3Jk\r\n'    
<response_auth_success> ::= "235 " r"[^\r\n]+" "\r\n"

<request_mail_from> ::= 'MAIL FROM:<sender@example.com>\r\n'
<response_mail_from> ::= "250 " r"[^\r\n]+" "\r\n"
<request_rcpt_to> ::= <rcpt_simple>
<rcpt_simple> ::= 'RCPT TO:<recipient@example.com>\r\n'

<response_rcpt_to> ::= "250 " r"[^\r\n]+" "\r\n"
<response_rcpt_to_repeated> ::= "250 " r"[^\r\n]+" "\r\n"
<request_data> ::= 'DATA\r\n'
<response_data> ::= r"[2-5][0-9]{2}" " " r"[^\r\n]+" "\r\n"

<email_content> ::= 'Subject: Metamorphic Test\r\n\r\nTesting repeated recipient behavior.\r\n.\r\n'
<response_emailA_sent> ::= "250 " r"[^\r\n]+" "\r\n"
<response_emailB_sent> ::= r"[2-5][0-9]{2}" " " r"[^\r\n]+" "\r\n"
<request_quit> ::= 'QUIT\r\n'
<response_quit> ::= "221 " r"[^\r\n]+" "\r\n"

where validateResponses(<response_emailA_sent>, <response_emailB_sent>) and validateRcptResponse(<response_rcpt_to>) and validateRcptResponse(<response_rcpt_to_repeated>)

