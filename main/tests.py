from django.test import TestCase

# Create your tests here.
import smtplib

server = smtplib.SMTP("mail.pinesofttechnologies.co.za", 587)
server.ehlo()
server.starttls()
server.ehlo()
server.login("dev@pinesofttechnologies.co.za", "Pinesoft#2030")
