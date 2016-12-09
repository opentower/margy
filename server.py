#! /usr/bin/env python

# Libraries
import smtpd
import asyncore
import sys
import os
import re
import PyPDF2
import StringIO
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
#-address with capture group for the recipient
recip = re.compile(r"(" + emailchar + r"+)@" + emailchar + r"+\." + emailchar + r"+")

#EMAIL HANDLERS

#Deals with emails sent to whitelist@margymail.com (beta only)
def whitelist_handler(replyadr):
    if replyadr not in open('static/whitelist.txt').read():
        wl = open('static/whitelist.txt', 'a')
        wl.write(replyadr + '\r\n')
        EmailUtils.text_message('MARGY@margymail.com',replyadr,'Whitelist Addition','Your email address has been added to MARGY\'s whitelist. Thank you for helping beta test MARGY!')
        wl.close
        return
    else:
        EmailUtils.text_message('MARGY@margymail.com',replyadr,'Already on Whitelist','A request was received to add this email address to MARGY\'s whitelist, but the address is already on the list. Thank you for helping beta test MARGY!')
        return

#Forwards emails sent to admin@margymail.com to faraci@gmail.com
def admin_handler(data,log):
    EmailUtils.forward_message(data,'faraci@gmail.com')
    log.write('Forwarded.\r\n')
    return

#Replies with an error if the mailto code is too short
def too_short_handler(replyadr,recipient,log):
    with app.app_context():
        shorttxt = render_template('code_failure.txt',code=recipient)
        short = render_template('code_failure.html',code=recipient)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',shorttxt,short)
    log.write(recipient + 'is too short. Failure message sent to ' + replyadr + '.\r\n')
    return

#Replies with an error if no match is found for the mailto code in metadata.txt
def no_match_handler(replyadr,recipient,log):
    with app.app_context():
        errortxt = render_template('code_failure.txt',code=recipient)
        error = render_template('code_failure.html',code=recipient)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',errortxt,error)
    log.write(recipient + 'not in metadata. Failure message sent to ' + replyadr + '.\r\n')
    return

#Replies with an error if no such file is found in letters/
def no_such_file_handler(replyadr,cfn,log):
    with app.app_context():
        nofiletxt = render_template('file_failure.txt',cfn=cfn)
        nofile = render_template('file_failure.html',cfn=cfn)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',nofiletxt,nofile)
    log.write('File not found. Failure message sent to ' + replyadr + '.\r\n')
    return

#Replies with an error if the file is corrupt
def corrupt_file_handler(replyadr,cfn,log):
    with app.app_context():
        corrupttxt = render_template('corrupt_failure.txt',file=cfn)
        corrupt = render_template('corrupt_failure.html',file=cfn)
    maybepdf.close()
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',corrupttxt,corrupt)
    log.write('Corrupt file. Failure message sent to ' + replyadr + '.\r\n')
    return

#Delivers the letter to a whitelisted address
def delivery_handler(match,rfn,rln,afn,aln,attach,cfn,log):
    with app.app_context():
       toedutxt = render_template('delivery.txt',rfn=rfn,rln=rln,afn=afn,aln=aln)
       toedu = render_template('delivery.html',rfn=rfn,rln=rln,afn=afn,aln=aln)
    applicant = afn + ' ' + aln
    subject = 'Letter Delivery for ' + applicant
    EmailUtils.rich_message('MARGY@margymail.com',match,subject,toedutxt,toedu,attach,cfn)
    log.write('Delivery made to ' + match + '.\r\n')
    return

#Replies with an error if there are no whitelisted addresses present
def not_whitelisted_handler(replyadr,log):
    with app.app_context():
       wlfailtxt = render_template('wl_failure.txt')
       wlfail = render_template('wl_failure.html')
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',wlfailtxt,wlfail)
    log.write('No whitelisted addresses present. Failure message sent to ' + replyadr + '.\r\n')
    return

#Sends the applicant a confirmation noting whitelisted addresses sent to and any requested addresses not sent to
def applicant_confirmation_handler(aem,rfn,rln,afn,aln,cfn,sentto,fsent,log):
    with app.app_context():
        toapptxt = render_template('del_confirm.txt',rfn=rfn,rln=rln,afn=afn,aln=aln,cfn=cfn,sentto=sentto,failed=fsent)
        toapp = render_template('del_confirm.html',rfn=rfn,rln=rln,afn=afn,aln=aln,cfn=cfn,sentto=sentto,failed=fsent)
    EmailUtils.rich_message('MARGY@margymail.com',aem,'Letter Delivery Confirmation',toapptxt,toapp)
    log.write('Confirmation sent to ' + aem + '.\r\n')
    return

#Replies with a confirmation noting whitelisted addresses sent to and any requested addresses not sent to
def sender_confirmation_handler(replyadr,rfn,rln,afn,aln,cfn,sentto,fsent,log):
    with app.app_context():
        tosendertxt = render_template('del_confirm.txt',rfn=rfn,rln=rln,afn=afn,aln=aln,cfn=cfn,sentto=sentto,failed=fsent)
        tosender = render_template('del_confirm.html',rfn=rfn,rln=rln,afn=afn,aln=aln,cfn=cfn,sentto=sentto,failed=fsent)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Confirmation',tosendertxt,tosender)
    log.write('Confirmation sent to ' + replyadr + '.\r\n')
    return

#SERVER

class MargySMTPServer(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data):
        log = open('serverlog.txt', 'a') #The log will be removed once MARGY is out of beta.
        log.write('\r\n')
        print 'Receiving...'
        #log the incoming message
        log.write('Receiving message from:' + str(peer) + '\r\n' )
        log.write('Message addressed from:' + str(mailfrom) + '\r\n' )
        log.write('Message addressed to  :' + str(rcpttos) + '\r\n' )
        log.write('Message length        :' + str(len(data)) + '\r\n' + '\r\n')
        parser = Parser()
        msg = parser.parsestr(data)
        matches = [] #initialize matches for accumulation
        for part in msg.walk(): #get matches only from text/html and text/plain parts of an email
            if part.get_content_type() in ['text/plain','text/html']:
                matches = matches + re.findall(email,part.get_payload())
        matches = list(set(matches)) #deduplicate match list
        if 'reply-to' in msg: replyadr = msg['reply-to']
        else: replyadr = str(mailfrom) #checks for a reply-to address; if not present, assigns sender as reply-to address
        for addr in rcpttos: #handle multiple addresses
	    recipient = re.match(recip, addr).group(1)
            if recipient.lower() == 'whitelist': #for emails sent to whitelist@margymail.com (beta only)
                whitelist_handler(replyadr)
            else:
                if recipient.lower() == 'admin': #for emails sent to admin@margymail.com
                    admin_handler(data,log)
                else:
                    if len(recipient) < 11: #makes sure the mailto code isn't too short
                        too_short_handler(replyadr,recipient,log)
                    else:
                        filecode = recipient[:-10] #scrapes all but the last 10 characters of the mailto code to serve as filecode (e.g., 'Test' from Test_123456789)
                        key = recipient[-9:] #scrapes the final 9 characters of the mailto code to serve as key (e.g., '123456789' from Test_123456789)
                        f = open('metadata.txt', 'r') #opens the file containing the metadata
                        mdata = 'empty' #set in case there is no metadata for the filecode
                        for line in f: #checks whether the filecode matches the first entry on each line of metadata and, if so, scrapes the line
                            if filecode.lower() == line.rstrip().lower()[:len(filecode)]:
                                mdata = line #
                                break
                        f.close()
                        if mdata == 'empty': #deals with cases where there is no metadata for the filecode
                            no_match_handler(replyadr,recipient,log)
                        else:
                            array = mdata.split() #creates a list out of the relevant line of metadata
                            cfn = array[0] + '.pdf' #assigns the first item in the metadata list as the file name (should be the same as filecode)
                            path = 'letters/' + cfn + '.aes' #the path to the file to be attached should be letters/[value of cfn].aes
                            if not os.path.isfile(path): #checks whether there is such a file
                                no_such_file_handler(replyadr,cfn,log)
                            else:
                                attach = f_decrypt(path, key) #assigns decrypted file as attachment
                                maybepdf = StringIO.StringIO(attach) #checks to make sure the file isn't corrupt
                                try:
                                    PyPDF2.PdfFileReader(maybepdf)
                                except PyPDF2.utils.PdfReadError:
                                    corrupt_file_handler(replyadr,cfn,log)
                                else:
                                    maybepdf.close()
                                    rfn = array[1].replace('_', ' ') #assigns the items of the metadata list to variables; this is recommender's first name
                                    rln = array[2].replace('_', ' ') #recommender's last name
                                    afn = array[3].replace('_', ' ') #applicant's first name
                                    aln = array[4].replace('_', ' ') #applicant's last name
                                    aem = array[5] #applicant's email address
                                    sentto = "" #creates an empty variable for whitelisted addresses that will receive attachment
                                    failed = [] #creates an empty list for non-whitelisted addresses that will not receive attachment
                                    for match in matches + [replyadr]: #checks each email address in the body and the reply-to address against the whitelist
                                       wl = open('static/whitelist.txt')
                                       for line in wl:
                                           if ( match.lower() == line.rstrip().lower() and match not in sentto.strip().lower() ):
                                               delivery_handler(match,rfn,rln,afn,aln,attach,cfn,log)
                                               sentto += match + ' ' #adds to the variable that contains whitelisted addresses that have been sent attachment
                                           else:
                                               failed.append(match) #adds to the list of non-whitelisted addresses that have not been sent attachment
                                       wl.close()
                                    fsent = "" #creates an empty variable for...
                                    for miss in failed: #...deduplication and removal of reply-to address from the list of failed recipients
                                        if ( miss.lower() != replyadr.lower() and miss.lower() not in sentto.strip().lower() and miss.lower() not in fsent.strip().lower() ):
                                            fsent += miss + ' '
                                            log.write('Delivery failed to ' + line + '.\r\n')
                                    if sentto == "": #deals with cases where there were no whitelisted addresses
                                        not_whitelisted_handler(replyadr,log)
                                    else: #sends confirmations to the applicant and the reply-to address (if attachment was sent anywhere)
                                        applicant_confirmation_handler(aem,rfn,rln,afn,aln,cfn,sentto,fsent,log)
                                        if ( replyadr.lower() != aem.lower()):
                                           sender_confirmation_handler(replyadr,rfn,rln,afn,aln,cfn,sentto,fsent,log)
        log.write('End of log entry.')
        log.close()
        print 'Done.'
        return

#Listen to port 25 ( 0.0.0.0 can be replaced by the ip of your server but that will work with 0.0.0.0 )
server = MargySMTPServer(('0.0.0.0', 25), None)

# Wait for incoming emails
asyncore.loop()
