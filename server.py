#! /usr/bin/env python

# Libraries
import smtpd
import asyncore
import sys
import os
import re
from outgoing_email import EmailUtils
from flask import Flask, render_template
from email.parser import Parser

app = Flask(__name__)

print 'Starting custom mail server'

#Regexes for processing email
email = re.compile(r"[^@ \n]+@[^@ \n]+\.[^@ \n]+")

class CustomSMTPServer(smtpd.SMTPServer):

    def process_message(self, peer, mailfrom, rcpttos, data):
        print 'Receiving message from:', peer
        print 'Message addressed from:', mailfrom
        print 'Message addressed to  :', rcpttos
        print 'Message length        :', len(data)
        parser = Parser()
        msg = parser.parsestr(data)
        matches = [] #initialize matches for accumulation
        for part in msg.walk(): #get matches only from text/html and text/plain parts of an email
            if part.get_content_type() in ['text/plain','text/html']:
                matches = matches + re.findall(email,part.get_payload())
        matches = list(set(matches)) #deduplicate match list
        if 'reply-to' in msg: replyadr = msg['reply-to']
        else: replyadr = str(mailfrom)
        print replyadr
        if 'admin@' in str(rcpttos):
            print "Forwarded"
            EmailUtils.forward_message(data,'faraci@gmail.com')
        else:
            end = len(str(rcpttos)) - 28
            code = ""
            for char in str(rcpttos)[2:end]:
                code += char
            f = open('metadata.txt', 'r')
            for line in f:
                print code.lower()
                print line.rstrip().lower()
                if code.lower() == line.rstrip().lower()[:len(code)]:
                    mdata = line
                    break
            f.close()
            try:
                mdata
            except NameError:
                pltxta = 'MARGY received a request for Letter Code ' + code + 'from this address. That code does not match any files in MARGY\'s database. For questions, or if you believe you received this email in error, please contact admin@margymail.com.'
                with app.app_context():
                    error = render_template('code_failure.html',code=code)
                EmailUtils.rich_message('MARGY@margybeta.davidfaraci.com',replyadr,'Letter Delivery Failure',pltxta,error)
                print code + '.pdf does not exist. Failure message sent to ' + replyadr + '.'
            else:
                array = mdata.split()
                cfn = array[0]
                if cfn[-4:] != '.pdf':
                    cfn += '.pdf'
                attach = 'letters/' + cfn
                rfn = array[1].replace('_', ' ')
                rln = array[2].replace('_', ' ')
                afn = array[3].replace('_', ' ')
                aln = array[4].replace('_', ' ')
                aem = array[5]
                with app.app_context():
                    toedu = render_template('delivery.html',rfn=rfn,rln=rln,afn=afn,aln=aln)
                sentto = ""
                pltxtb = 'Please find attached a letter of recommendation from ' + rfn + ' ' + rln + 'for ' + afn + ' ' + aln + '. This email has been generated by MARGY, an automated management system for confidential letters of recommendation. For more information about this service, visit http://margymail.com. For questions, or if you believe you received this email in error, please contact admin@margymail.com.'
                for match in matches + [replyadr]:
                    wl = open('static/whitelist.txt')
                    for line in wl:
                        print match
                        print line
                        if ( match.lower() == line.rstrip().lower() and match not in sentto.strip() ):
                            print 'match'
                            EmailUtils.rich_message('MARGY@margybeta.davidfaraci.com',match,'Letter Delivery',pltxtb,toedu,attach)
                            sentto += match + " "
                            print 'Delivery made to ' + match
                pltxtc = 'MARGY received a request from this address, but was unable to complete the requested delivery as none of the addresses present are on MARGY\'s whitelist.'
                pltxtd = 'MARGY has made the following delivery:' + '\r\n' + '\r\n' + 'File Name: ' + cfn + '\r\n' + 'Letter-Writer: ' + rfn  + ' ' + rln + '\r\n' + 'Applicant: ' + afn + ' ' + aln + '\r\n' + 'Recipients: ' + str(sentto) + '\r\n' + '\r\n' + 'Confirmation emails have been sent to the applicant and to the email address that sent the request (if different). For questions, or if you believe you received this email in error, please contact admin@margymail.com.' + '\r\n' + 'MARGY'
                with app.app_context():
                    toapp = render_template('del_confirm.html',rfn=rfn,rln=rln,afn=afn,aln=aln,cfn=cfn,sentto=sentto)
                    wlfail = render_template('wl_failure.html')
                if sentto == '':
                    EmailUtils.rich_message('MARGY@margybeta.davidfaraci.com',replyadr,'Letter Delivery Failure',pltxtc,wlfail)
                    print 'No whitelisted addresses present. Failure message sent to ' + replyadr + '.'
                else:
                    if aem not in sentto.split():
                        EmailUtils.rich_message('MARGY@margybeta.davidfaraci.com',aem,'Letter Delivery Confirmation',pltxtd,toapp)
                        print 'Confirmation sent to ' + aem
                    if ( replyadr.lower() != aem.lower() and replyadr not in sentto.split() ):
                        EmailUtils.rich_message('MARGY@margybeta.davidfaraci.com',replyadr,'Letter Delivery Confirmation',pltxtd,toapp)
                        print 'Confirmation sent to ' + replyadr
        return

#Listen to port 25 ( 0.0.0.0 can be replaced by the ip of your server but that will work with 0.0.0.0 )
server = CustomSMTPServer(('0.0.0.0', 25), None)

# Wait for incoming emails
asyncore.loop()
