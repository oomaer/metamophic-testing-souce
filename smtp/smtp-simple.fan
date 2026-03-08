include ("smtp-utils.fan")

<start> ::= <Interaction1>

# --- INTERACTION 1  
<Interaction1> ::= <ServerA:banner> <CONN1>
<CONN1> ::= <EHLO_ex1> <MAIL_ex1> <RCPT_ex1_A> <RCPT_ex1_B> <RCPT_ex1_C> <DATA_ex1> <QUIT_ex1>

<StopConnection1> ::= "Stopping connection 1 and starting connection 2" := changeConnection()

# --- INTERACTION 2 
<Interaction2> ::= <ServerB:banner> <CONN2>
<CONN2> ::= <EHLO_ex2> <MAIL_ex2> <RCPT_ex2_C> <RCPT_ex2_B> <RCPT_ex2_A> <DATA_ex2> <QUIT_ex2>

# Interaction 1 
<EHLO_ex1> ::= <ClientA:EHLO> <ServerA:ehlo_response>
<MAIL_ex1> ::= <ClientA:MAIL> <ServerA:positive_response>
<RCPT_ex1_A> ::= <ClientA:RCPT_A> <ServerA:positive_response>
<RCPT_ex1_B> ::= <ClientA:RCPT_B> <ServerA:positive_response>
<RCPT_ex1_C> ::= <ClientA:RCPT_C> <ServerA:positive_response>
<DATA_ex1> ::= <ClientA:DATA> <ServerA:DATA_response> <ClientA:MAIL_DATA> <ServerA:positive_response>
<QUIT_ex1> ::= <ClientA:QUIT> <ServerA:quit_response>

# Interaction 2 
<EHLO_ex2> ::= <ClientB:EHLO> <ServerB:ehlo_response>
<MAIL_ex2> ::= <ClientB:MAIL> <ServerB:positive_response>
<RCPT_ex2_A> ::= <ClientB:RCPT_A> <ServerB:positive_response>
<RCPT_ex2_B> ::= <ClientB:RCPT_C> <ServerB:positive_response>
<RCPT_ex2_C> ::= <ClientB:RCPT_B> <ServerB:positive_response>
<DATA_ex2> ::= <ClientB:DATA> <ServerB:DATA_response> <ClientB:MAIL_DATA> <ServerB:positive_response>
<QUIT_ex2> ::= <ClientB:QUIT> <ServerB:quit_response>

# Client Commands 
<EHLO> ::= "EHLO localhost" <crlf>
<MAIL> ::= "MAIL FROM:<sender@test.com>" <crlf>
<RCPT_A> ::= "RCPT TO:<alpha@example.com>" <crlf>
<RCPT_B> ::= "RCPT TO:<alpha@example.com>" <crlf>
<RCPT_C> ::= "RCPT TO:<alpha@example.com>" <crlf>
<DATA> ::= "DATA" <crlf>
<MAIL_DATA> ::= "Subject: Test" <crlf> <crlf> "Body" <crlf> "." <crlf>
<QUIT> ::= "QUIT" <crlf>

# Server Responses 
<banner> ::= "220" <space> <text> <crlf>
<ehlo_response> ::= <ehlo_line>+ <ehlo_last_line>
<ehlo_line> ::= "250-" <text> <crlf>
<ehlo_last_line> ::= "250 " <text> <crlf>
<positive_response> ::= "250 " <text> <crlf>

<DATA_response> ::= "354 " <text> <crlf>
<quit_response> ::= "221 " <text> <crlf>

<space> ::= " "
<crlf> ::= "\r\n"
<text> ::= r"[^\r\n]*" := "ok"