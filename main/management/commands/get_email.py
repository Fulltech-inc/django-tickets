"""
This file was derived from:
https://github.com/rossp/django-helpdesk/blob/master/helpdesk/management/commands/get_email.py

Copyright notice for that original file:

Copyright (c) 2008, Ross Poulton (Trading as Jutda)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    3. Neither the name of Ross Poulton, Jutda, nor the names of any
       of its contributors may be used to endorse or promote products
       derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import email
import imaplib
import mimetypes
import re
import os
from email.header import decode_header
from email.utils import parseaddr, collapse_rfc2231_value
from email_reply_parser import EmailReplyParser
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

try:
    from django.utils import timezone
except ImportError:
    from datetime import datetime as timezone

from main.models import Ticket, Attachment, FollowUp


class Command(BaseCommand):
    help = 'Process email inbox and create tickets.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-q', '--quiet',
            action='store_true',
            default=False,
            help='Hide details about each message as they are processed.'
        )

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        process_inbox(quiet=quiet)


def process_inbox(quiet=False):
    """
    Connects to IMAP inbox and processes all new emails
    """
    # Connect to IMAP server with SSL on port 993 (standard)
    server = imaplib.IMAP4_SSL(
        os.environ["DJANGO_TICKET_INBOX_SERVER"], 993
    )
    server.login(
        os.environ["DJANGO_TICKET_INBOX_USER"],
        os.environ["DJANGO_TICKET_INBOX_PASSWORD"]
    )
    server.select("INBOX")

    # Search for all emails not marked deleted
    status, data = server.search(None, 'NOT', 'DELETED')
    if data:
        msgnums = data[0].split()
        for num in msgnums:
            status, msg_data = server.fetch(num, '(RFC822)')
            if status != 'OK':
                continue
            raw_email = msg_data[0][1]
            ticket_or_followup = ticket_from_message(message_bytes=raw_email, quiet=quiet)
            if ticket_or_followup and not quiet:
                print(f"Processed message for ticket/followup: {ticket_or_followup}")
            # Mark message deleted after processing
            server.store(num, '+FLAGS', '\\Deleted')

    server.expunge()
    server.close()
    server.logout()


def decode_unknown(value, charset='utf-8'):
    if isinstance(value, bytes):
        try:
            return value.decode(charset, errors='ignore')
        except Exception:
            return value.decode('iso8859-1', errors='ignore')
    elif isinstance(value, str):
        return value
    else:
        return str(value)


def decode_mail_headers(string):
    decoded = decode_header(string)
    return u' '.join([
        part if isinstance(part, str) else part.decode(charset or 'utf-8', errors='ignore')
        for part, charset in decoded
    ])


def ticket_from_message(message_bytes, quiet):
    """
    Create a ticket or a followup (if ticket id in subject)
    """
    message = email.message_from_bytes(message_bytes)

    subject = message.get('subject', 'Created from e-mail')
    subject = decode_mail_headers(subject)

    sender = message.get('from', 'Unknown Sender')
    sender = decode_mail_headers(sender)
    sender_email = parseaddr(sender)[1]

    body_plain, body_html = '', ''

    # Match ticket ID pattern in subject (e.g., "[#1234]")
    matchobj = re.search(r"\[#(\d+)\]", subject)
    ticket_id = int(matchobj.group(1)) if matchobj else None

    counter = 0
    files = []

    for part in message.walk():
        if part.get_content_maintype() == 'multipart':
            continue

        name = part.get_param("name")
        if name:
            name = collapse_rfc2231_value(name)

        if part.get_content_maintype() == 'text' and name is None:
            if part.get_content_subtype() == 'plain':
                charset = part.get_content_charset() or 'utf-8'
                payload = part.get_payload(decode=True)
                body_plain = EmailReplyParser.parse_reply(payload.decode(charset, errors='ignore'))
            else:
                body_html = part.get_payload(decode=True)
        else:
            if not name:
                ext = mimetypes.guess_extension(part.get_content_type()) or ''
                name = f"part-{counter}{ext}"

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

    if ticket_id:
        try:
            t = Ticket.objects.get(id=ticket_id)
            new = False
        except Ticket.DoesNotExist:
            ticket_id = None

    if ticket_id is None:
        users = User.objects.all()
        email_addresses = [user.email for user in users]

        # Check if subject contains valid ticket ID to create followup
        tickets = Ticket.objects.all()
        ticket_ids = [t.id for t in tickets]

        subject_id_match = re.search(r'\[#(\d+)\]', subject)
        subject_id = int(subject_id_match.group(1)) if subject_id_match else None

        if subject_id in ticket_ids:
            # Create followup
            if sender_email in email_addresses:
                f = FollowUp(
                    title=subject,
                    created=now,
                    text=body,
                    ticket=Ticket.objects.get(id=subject_id),
                    user=User.objects.get(email=sender_email),
                )
            else:
                f = FollowUp(
                    title=subject,
                    created=now,
                    text=body,
                    ticket=Ticket.objects.get(id=subject_id),
                )
            f.save()
            if not quiet:
                print(f"Created followup for ticket #{subject_id}")
            return f
        else:
            # Create new ticket
            if sender_email in email_addresses:
                t = Ticket(
                    title=subject,
                    status="TODO",
                    created=now,
                    description=body,
                    owner=User.objects.get(email=sender_email),
                )
            else:
                t = Ticket(
                    title=subject,
                    status="TODO",
                    created=now,
                    description=body,
                )
            t.save()

            from django.core.mail import send_mail
            notification_subject = f"[#{t.id}] New ticket created"
            notification_body = f"Hi,\n\na new ticket was created: http://localhost:8000/ticket/{t.id}/"
            send_mail(
                notification_subject,
                notification_body,
                os.environ["DJANGO_TICKET_EMAIL_NOTIFICATIONS_FROM"],
                [os.environ["DJANGO_TICKET_EMAIL_NOTIFICATIONS_TO"]],
                fail_silently=False,
            )
            if not quiet:
                print(f"Created new ticket #{t.id}")

            return t

    elif t.status == Ticket.CLOSED_STATUS:
        t.status = Ticket.REOPENED_STATUS
        t.save()
        if not quiet:
            print(f"Reopened ticket #{t.id}")

    # Save attachments
    for file in files:
        if file['content']:
            filename = re.sub(r'[^a-zA-Z0-9._-]+', '', file['filename'].replace(' ', '_').encode('ascii', 'replace').decode('ascii'))
            if ticket_id:
                attachment = Attachment(
                    ticket=Ticket.objects.get(id=ticket_id),
                    filename=filename,
                    # mime_type=file['type'],
                    # size=len(file['content']),
                )
            else:
                attachment = Attachment(
                    ticket=t,
                    filename=filename,
                    # mime_type=file['type'],
                    # size=len(file['content']),
                )
            attachment.file.save(filename, ContentFile(file['content']), save=False)
            attachment.save()

            if not quiet:
                print(f" - Saved attachment: {filename}")

    return t
