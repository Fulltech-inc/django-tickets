A simple ticketing application
==============================

`django-tickets` is a simple MIT-licensed ticketing application written in Python/Django. Some of the features are:

- creation of new tickets via web interface or via email
- followups on tickets
- file attachments for tickets
- assign tickets to users
- email notifications for new assignments, followups and closed tickets

The application was written to serve my special needs.  It is not intended to grow up to a kitchen sink.  But I will add some features in the future.  Feel free to use and modify it, if it is interesting for you.



Installation
============

Sensitive and installation dependent information is expected in environment variables. You can use a bash script like this one:

```
Put text here!

# Command to turn on escalation module
python manage.py run_escalation
```