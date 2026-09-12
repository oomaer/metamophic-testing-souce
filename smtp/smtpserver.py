import argparse
import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult

# This tells the server: "If they try to log in, just say yes."
def easy_authenticator(server, session, envelope, mechanism, auth_data):
    print(f"🔑 Authentication attempt - User: {auth_data.login.decode()}")
    return AuthResult(success=True)  # Accept any login

class SMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        print(f"📧 Message from {envelope.mail_from} to {envelope.rcpt_tos}")
        return f"250 OK {envelope.mail_from} {envelope.rcpt_tos}"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run SMTP test server')
    parser.add_argument('-p', '--port', type=int, default=8025, help='Port to listen on (default: 8025)')
    args = parser.parse_args()
    
    # We add the authenticator here
    controller = Controller(
        SMTPHandler(), 
        hostname='127.0.0.1', 
        port=args.port,
        authenticator=easy_authenticator,
        auth_required=True,  # This makes authentication optional
        auth_require_tls=False # Allows plain text login for testing
    )
    controller.start()
    print(f"Server is running on port {args.port} (AUTH REQUIRED). Press Ctrl+C to stop.")
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        controller.stop()