#! /usr/bin/env python

# Libraries
import smtpd
import asyncore
import sys
import os
import re
from outgoing_email import EmailUtils
from flask import Flask, render_template, request
from email.parser import Parser
from encryption import f_decrypt

app = Flask(__name__)

print 'Starting custom mail server'

#Regexes for processing email
#-negation of typically forbidden characters, as well as quotation marks, which we stipulate are ridiculous and do not belong in email addresses.
emailchar = r"[^@ \n\(\)\,\:\;\<\>\[\\\]\"]" 
#-the actual regex for an address
email = re.compile(emailchar + r"+@" + emailchar + r"+\." + emailchar + r"+")

class CustomSMTPServer(smtpd.SMTPServer):

    def process_message(self, peer, mailfrom, rcpttos, data):
        log = open('serverlog.txt', 'a') #The log will be removed once MARGY is out of beta.
        log.write('\r\n')
        print 'Receiving...'
        #log the incoming message
        log.write('Receiving message from:' + str(peer))
        log.write('Message addressed from:' + str(mailfrom))
        log.write('Message addressed to  :' + str(rcpttos))
        log.write('Message length        :' + str(len(data)) + '\r\n' + '\r\n')
        parser = Parser()
        msg = parser.parsestr(data)
        matches = [] #initialize matches for accumulation
        for part in msg.walk(): #get matches only from text/html and text/plain parts of an email
            if part.get_content_type() in ['text/plain','text/html']:
                matches = matches + re.findall(email,part.get_payload())
        matches = list(set(matches)) #deduplicate match list
        if 'reply-to' in msg: replyadr = msg['reply-to']
        else: replyadr = str(mailfrom)
        n = 0
        for addr in rcpttos: #handle multiple addresses
            if str(rcpttos[n])[:9] == 'whitelist':
                if replyadr not in open('static/whitelist.txt').read():
                    wl = open('static/whitelist.txt', 'a')
                    wl.write(replyadr + '\r\n')
                    EmailUtils.text_message('MARGY@margymail.com',replyadr,'Whitelist Addition','Your email address as been added to MARGY\'s whitelist. Thank you for helping beta test MARGY!')
                    wl.close
                else:
                    EmailUtils.text_message('MARGY@margymail.com',replyadr,'Already on Whitelist','A request was received to add this email address to MARGY\'s whitelist, but the address is already on the list. Thank you for helping beta test MARGY!')
            else:
                if str(rcpttos[n])[:5] == 'admin':
                    EmailUtils.forward_message(data,'faraci@gmail.com')
                    log.write('Forwarded.\r\n')
                else:
                    end = len(str(rcpttos[n])) - 14
                    code = ""
                    for char in str(rcpttos[n])[:end]:
                        code += char
                    if len(code) < 11:
                        with app.app_context():
                            shorttxt = render_template('code_failure.txt',code=code)
                            short = render_template('code_failure.html',code=code)
                        EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',shorttxt,short)
                        log.write(code + 'not in metadata. Failure message sent to ' + replyadr + '.\r\n')
                    else:
                        filecode = code[:-10]
                        key = code[-9:]
                        f = open('metadata.txt', 'r')
                        mdata = 'empty'
                        for line in f:
                            if filecode.lower() == line.rstrip().lower()[:len(filecode)]:
                                mdata = line
                                break
                        f.close()
                        if mdata == 'empty':
                            with app.app_context():
                                errortxt = render_template('code_failure.txt',code=code)
                                error = render_template('code_failure.html',code=code)
                            EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',errortxt,error)
                            log.write(code + 'not in metadata. Failure message sent to ' + replyadr + '.\r\n')
                        else:
                            array = mdata.split()
                            cfn = array[0] + '.pdf'
                            path = 'letters/' + cfn + '.aes'
                            if not os.path.isfile(path):
                                with app.app_context():
                                    nofiletxt = render_template('file_failure.txt',cfn=cfn)
                                    nofile = render_template('file_failure.html',cfn=cfn)
                                EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',nofiletxt,nofile)
                                log.write('File not found. Failure message sent to ' + replyadr + '.\r\n')
                            else:
                                attach = f_decrypt(path, key)
                                rfn = array[1].replace('_', ' ')
                                rln = array[2].replace('_', ' ')
                                afn = array[3].replace('_', ' ')
                                aln = array[4].replace('_', ' ')
                                aem = array[5]
                                with app.app_context():
                                    toedutxt = render_template('delivery.txt',rfn=rfn,rln=rln,afn=afn,aln=aln)
                                    toedu = render_template('delivery.html',rfn=rfn,rln=rln,afn=afn,aln=aln)
                                sentto = ""
                                failed = []
                                for match in matches + [replyadr]:
                                    wl = open('static/whitelist.txt')
                                    for line in wl:
                                        if ( match.lower() == line.rstrip().lower() and match not in sentto.strip().lower() ):
                                            applicant = afn + ' ' + aln
                                            subject = 'Letter Delivery for ' + applicant
                                            EmailUtils.rich_message('MARGY@margymail.com',match,subject,toedutxt,toedu,attach,cfn)
                                            sentto += match
                                            log.write('Delivery made to ' + match + '.\r\n')
                                        else:
                                            failed.append(match)
                                    wl.close()
                                fsent = ""
                                for miss in failed:
                                    if ( miss.lower() != replyadr.lower() and miss.lower() not in sentto.strip().lower() and miss.lower() not in fsent.strip().lower() ):
                                        fsent += miss + ' '
                                        log.write('Delivery failed to ' + line + '.\r\n')
                                with app.app_context():
                                    toapptxt = render_template('del_confirm.txt',rfn=rfn,rln=rln,afn=afn,aln=aln,cfn=cfn,sentto=sentto,failed=fsent)
                                    toapp = render_template('del_confirm.html',rfn=rfn,rln=rln,afn=afn,aln=aln,cfn=cfn,sentto=sentto,failed=fsent)
                                    wlfailtxt = render_template('wl_failure.txt')
                                    wlfail = render_template('wl_failure.html')
                                if sentto == "":
                                    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',wlfailtxt,wlfail)
                                    log.write('No whitelisted addresses present. Failure message sent to ' + replyadr + '.\r\n')
                                else:
                                    if aem.lower() not in sentto.strip().lower():
                                        EmailUtils.rich_message('MARGY@margymail.com',aem,'Letter Delivery Confirmation',toapptxt,toapp)
                                        log.write('Confirmation sent to ' + aem + '.\r\n')
                                    if ( replyadr.lower() != aem.lower() and replyadr.lower() not in sentto.strip().lower() ):
                                        EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Confirmation',toapptxt,toapp)
                                        log.write('Confirmation sent to ' + replyadr + '.\r\n')
            n += 1
        log.write('End of log entry.')
        log.close()
        print 'Done.'
        return

#Listen to port 25 ( 0.0.0.0 can be replaced by the ip of your server but that will work with 0.0.0.0 )
server = CustomSMTPServer(('0.0.0.0', 25), None)

# Wait for incoming emails
asyncore.loop()
