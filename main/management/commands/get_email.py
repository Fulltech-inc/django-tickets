import email
import imaplib
import mimetypes
import re
import os
from email.header import decode_header
from email.utils import parseaddr, collapse_rfc2231_value
from optparse import make_option
from email_reply_parser import EmailReplyParser
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from main.models import Ticket, Attachment, FollowUp

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Hide details about each message as they are processed.'
        )

    help = 'Process email inbox and create tickets.'

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        process_inbox(quiet=quiet)

def process_inbox(quiet=False):
    server = imaplib.IMAP4_SSL(os.environ["DJANGO_TICKET_INBOX_SERVER"], 993)
    server.login(os.environ["DJANGO_TICKET_INBOX_USER"], os.environ["DJANGO_TICKET_INBOX_PASSWORD"])
    server.select("INBOX")
    status, data = server.search(None, 'NOT', 'DELETED')
    if data:
        msgnums = data[0].split()
        for num in msgnums:
            status, data = server.fetch(num, '(RFC822)')
            ticket = ticket_from_message(message=data[0][1], quiet=quiet)
            if ticket:
                server.store(num, '+FLAGS', '\\Deleted')
    server.expunge()
    server.close()
    server.logout()

def decodeUnknown(value, charset='utf-8'):
    if isinstance(value, bytes):
        try:
            return value.decode(charset, errors='ignore')
        except:
            return value.decode('iso8859-1', errors='ignore')
    elif isinstance(value, str):
        return value
    else:
        return str(value)

def decode_mail_headers(string):
    decoded = decode_header(string)
    return u' '.join([
        msg if isinstance(msg, str) else msg.decode(charset or 'utf-8', errors='ignore')
        for msg, charset in decoded
    ])

def ticket_from_message(message, quiet):
    msg = message
    message = email.message_from_bytes(msg)
    subject = message.get('subject', 'Created from e-mail')
    subject = decode_mail_headers(subject)
    sender = message.get('from', 'Unknown Sender')
    sender = decode_mail_headers(sender)
    sender_email = parseaddr(sender)[1]
    body_plain, body_html = '', ''

    ticket_id_from_subject = re.search(r'\[#(\d+)\]', subject)
    ticket = None
    if ticket_id_from_subject:
        try:
            ticket = Ticket.objects.get(id=ticket_id_from_subject.group(1))
        except Ticket.DoesNotExist:
            ticket = None

    files = []
    counter = 0
    for part in message.walk():
        if part.get_content_maintype() == 'multipart':
            continue

        name = part.get_param("name")
        if name:
            name = collapse_rfc2231_value(name)

        if part.get_content_maintype() == 'text' and name is None:
            if part.get_content_subtype() == 'plain':
                body_plain = EmailReplyParser.parse_reply(
                    decodeUnknown(part.get_payload(decode=True), part.get_content_charset())
                )
            else:
                body_html = part.get_payload(decode=True)
        else:
            if not name:
                ext = mimetypes.guess_extension(part.get_content_type())
                name = f"part-{counter}{ext or ''}"
            files.append({
                'filename': name,
                'content': part.get_payload(decode=True),
                'type': part.get_content_type(),
            })
        counter += 1

    body = body_plain or 'No plain-text email body available. Please see attachment email_html_body.html.'

    if body_html:
        files.append({
            'filename': 'email_html_body.html',
            'content': body_html,
            'type': 'text/html',
        })

    now = timezone.now()
    email_users = {u.email: u for u in User.objects.all() if u.email}

    if ticket:
        f = FollowUp(
            title=subject,
            created=now,
            text=body,
            ticket=ticket,
            user=email_users.get(sender_email)
        )
        f.save()
        target_ticket = ticket
    else:
        t = Ticket(
            title=subject,
            status="TODO",
            created=now,
            description=body,
            owner=email_users.get(sender_email)
        )
        t.save()
        from django.core.mail import send_mail
        send_mail(
            f"[#{t.id}] New ticket created",
            f"Hi,\n\na new ticket was created: http://5.189.181.199:8000/ticket/{t.id}/",
            os.environ["DJANGO_TICKET_EMAIL_NOTIFICATIONS_FROM"],
            [os.environ["DJANGO_TICKET_EMAIL_NOTIFICATIONS_TO"]],
            fail_silently=False
        )
        target_ticket = t

    for file in files:
        if file['content']:
            filename = re.sub(r'[^a-zA-Z0-9._-]+', '', file['filename'].replace(' ', '_'))
            a = Attachment(
                ticket=target_ticket,
                filename=filename,
            )
            a.file.save(filename, ContentFile(file['content']), save=False)
            a.save()
            if not quiet:
                print(f" - {filename}")

    return target_ticket
