#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Libraries
import smtpd
import asyncore
import sys
import io
import os
import re
import PyPDF2
import StringIO
import datetime
from outgoing_email import EmailUtils
from flask import Flask, render_template, request
from email.parser import Parser
from encryption import f_decrypt

def timeStamped(fname, fmt='%Y-%m-%d-%H-%M-%S_{fname}'):
    return datetime.datetime.now().strftime(fmt).format(fname=fname)

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

#Forwards emails sent to admin@margymail.com or postmaster@margymail.com to faraci@gmail.com
def admin_handler(data,log):
    EmailUtils.forward_message(data,'faraci@gmail.com')
    log.write(u'Forwarded.\r\n')
    return

#Forwards emails sent to list@margymail.com from permitted senders to blastlist
def list_handler(data,log,replyadr):
    sl = io.open('authorized', 'r', encoding='utf-8')
    auth = 0
    for line in sl:
        if replyadr.lower() in line.lower():
            auth = 1
    sl.close
    if auth == 0:
        EmailUtils.text_message('list@margymail.com',replyadr,'Unauthorized','You are not authorized to use this list.')
    elif auth == 1:
        bl = io.open('blastlist.txt','r', encoding='utf-8')
        for addr in bl:
            EmailUtils.forward_message(data,addr)
        bl.close

#Replies with an error if the mailto code is too short or has no underscore, and adds address to strikelist (for potential blacklisting)
def too_short_handler(replyadr,recipient,log):
    bl = io.open('blacklist', 'a+', encoding="utf-8")
    sl = io.open('strikelist', 'r', encoding="utf-8")
    strikes = 0
    for line in sl: #checks if address already strikelisted
        if replyadr.lower() in line.lower():
            strikes += 1
    sl.close()
    if strikes >= 2: #blacklists on third strike
        log.write(u'Strikelisted address ' + replyadr + u' added to blacklist.\r\n')
        bl.write(replyadr + '\r\n')
        sl = io.open('strikelist', 'r+', encoding="utf-8")
        slcont = sl.readlines()
        sl.seek(0)
        for entry in slcont:
            if replyadr.lower() not in entry.lower():
                sl.write(entry)
        sl.truncate()
        sl.close()
    else:
        log.write(u'Strike for ' + replyadr + u'.\r\n')
        sl = io.open('strikelist', 'a+', encoding="utf-8")
        sl.write(replyadr + u'\r\n')
        sl.close()
    bl.close()
    with app.app_context():
        shorttxt = render_template('code_failure.txt',code=recipient)
        short = render_template('code_failure.html',code=recipient)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',shorttxt,short)
    log.write(recipient + u' too short or no underscore.\r\n')
    return

#Replies with an error if no match is found for the mailto code in metadata.txt
def no_match_handler(replyadr,recipient,log):
    with app.app_context():
        errortxt = render_template('code_failure.txt',code=recipient)
        error = render_template('code_failure.html',code=recipient)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',errortxt,error)
    log.write(recipient + u' not in metadata.\r\n')
    return

#Replies with an error if no such file is found in letters/
def no_such_file_handler(replyadr,cfn,log):
    with app.app_context():
        nofiletxt = render_template('file_failure.txt',cfn=cfn)
        nofile = render_template('file_failure.html',cfn=cfn)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',nofiletxt,nofile)
    log.write(recipient + u': File not found.\r\n')
    return

#Replies with an error if the file is corrupt
def corrupt_file_handler(replyadr,cfn,log):
    with app.app_context():
        corrupttxt = render_template('corrupt_failure.txt',file=cfn)
        corrupt = render_template('corrupt_failure.html',file=cfn)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',corrupttxt,corrupt)
    log.write(recipient + u': Corrupt file.\r\n')
    return

#Delivers the letter to a whitelisted address
def delivery_handler(match,rfn,rln,afn,aln,attach,cfn,log):
    applicant = afn + ' ' + aln
    recs = rfn + ' ' + rln
    with app.app_context():
       toedutxt = render_template('delivery.txt',recs=recs,app=applicant,email=match)
       toedu = render_template('delivery.html',recs=recs,rln=rln,app=applicant,email=match)
    subject = 'Letter Delivery for ' + applicant
    EmailUtils.rich_message('MARGY@margymail.com',match,subject,toedutxt,toedu,attach,cfn)
    log.write(u'Delivery made to ' + match + u'.\r\n')
    return

#Replies with an error if there are no whitelisted addresses present
def not_whitelisted_handler(replyadr,log):
    with app.app_context():
       wlfailtxt = render_template('wl_failure.txt')
       wlfail = render_template('wl_failure.html')
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Failure',wlfailtxt,wlfail)
    log.write(u'No whitelisted addresses present.\r\n')
    return

#Sends the applicant a confirmation noting whitelisted addresses sent to and any requested addresses not sent to
def applicant_confirmation_handler(aem,rfn,rln,afn,aln,cfn,sentto,fsent,log):
    recs = rfn + ' ' + rln
    applicant = afn + ' ' + aln
    with app.app_context():
        toapptxt = render_template('del_confirm.txt',recs=recs,app=applicant,cfn=cfn,sentto=sentto,failed=fsent)
        toapp = render_template('del_confirm.html',recs=recs,app=applicant,cfn=cfn,sentto=sentto,failed=fsent)
    EmailUtils.rich_message('MARGY@margymail.com',aem,'Letter Delivery Confirmation',toapptxt,toapp)
    log.write(u'Confirmation sent.\r\n')
    return

#Replies with a confirmation noting whitelisted addresses sent to and any requested addresses not sent to
def sender_confirmation_handler(replyadr,rfn,rln,afn,aln,cfn,sentto,fsent,log):
    recs = rfn + ' ' + rln
    applicant = afn + ' ' + aln
    with app.app_context():
        tosendertxt = render_template('del_confirm.txt',recs=recs,app=applicant,cfn=cfn,sentto=sentto,failed=fsent)
        tosender = render_template('del_confirm.html',recs=recs,app=applicant,cfn=cfn,sentto=sentto,failed=fsent)
    EmailUtils.rich_message('MARGY@margymail.com',replyadr,'Letter Delivery Confirmation',tosendertxt,tosender)
    log.write(u'Confirmation sent.\r\n')
    return

#SERVER

class MargySMTPServer(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data):
        now = datetime.datetime.now().strftime("%m.%d.%Y %H:%M:%S")
        log = io.open('serverlog.txt', 'a', encoding="utf-8")
        log.write(u'\r\n' + now + u'\r\n')
        print '\r\n' + now  + '\r\nReceiving...'
        parser = Parser()
        msg = parser.parsestr(data)
        matches = [] #initialize matches for accumulation
        for part in msg.walk(): #get matches only from text/html and text/plain parts of an email
            if part.get_content_type() in ['text/plain','text/html']:
            	charset = part.get_content_charset()
            	if charset is None:
            		decoded = unicode(part.get_payload(decode=True),'latin1','replace')
            	else:
            		decoded = unicode(part.get_payload(decode=True), str(charset), 'replace')
		matches = matches + re.findall(email,decoded)
        matches = list(set(matches)) #deduplicate match list
        if 'reply-to' in msg: replyadr = msg['reply-to']
        else: replyadr = str(mailfrom).decode('utf-8') #checks for a reply-to address; if not present, assigns sender as reply-to address
        bl = io.open('blacklist', 'r', encoding="utf-8") #open blacklist (spam avoidance)
        blisted = 0
        for line in bl: #checks reply-to address against blacklist
            if replyadr.lower() in line.lower():
                log.write(u'Email blocked from blacklisted address ' + replyadr + u'.\r\n')
                print 'Blacklisted.'
                blisted = 1
        bl.close()
        if blisted == 1: #handles emails from blacklisted addresses
            warned = io.open('warned', 'r', encoding="utf-8") #checks whether this address has already been warned it was blacklisted
            wrn = 0
            for line in warned:
                if replyadr.lower() in line.lower():
                    wrn = 1
            if wrn == 0: #warns previously unwarned blacklisted addresses
                EmailUtils.text_message('MARGY@margymail.com',replyadr,'BLACKLISTED','You have sent too many nonstandard emails to this system; further emails from your address will not be processed. If you believe this is an error, please contact MARGY adminstration.')
                warned = io.open('warned', 'a+', encoding="utf-8") #adds reply-to address to list of warned addresses
                warned.write(replyadr + u'\r\n')
                warned.close()
        if blisted == 0:
            for addr in rcpttos: #handle multiple addresses
                recipient = re.match(recip, addr).group(1)
                if recipient.lower() == 'list':
                    list_handler(data,log,replyadr)
                elif ( recipient.lower() == 'admin' or recipient.lower() == 'postmaster' or recipient.lower() == 'abuse' ): #for emails sent to admin@ or postmaster@ or abuse@ or MARGY@margymail.com
                    admin_handler(data,log)
                else:
                    if ( recipient.lower() != 'sales' and recipient.lower() != 'info' and recipient.lower() != 'xderia' and recipient.lower() != 'margy' ): #ignores emails to sales@, info@, xderia@, and margy@ (the last to maintain confidentiality)
                        if ( len(recipient) < 11 or '_' not in recipient ): #makes sure the mailto code isn't too short and includes an underscore
                            too_short_handler(replyadr,recipient,log)
                        else:
                            filecode = recipient[:-10] #scrapes all but the last 10 characters of the mailto code to serve as filecode (e.g., 'Test' from Test_123456789)
                            key = recipient[-9:] #scrapes the final 9 characters of the mailto code to serve as key (e.g., '123456789' from Test_123456789)
                            f = io.open('metadata.txt', 'r', encoding="utf-8") #opens the file containing the metadata
                            mdata = 'empty' #set in case there is no metadata for the filecode
                            for line in f: #checks whether the filecode matches the first entry on each line of metadata and, if so, scrapes the line
                                if filecode.lower() == line.rstrip().lower()[:len(filecode)]:
                                    mdata = line
                                    break
                            f.close()
                            if mdata == 'empty': #deals with cases where there is no metadata for the filecode
                                no_match_handler(replyadr,recipient,log)
                            else:
                                array = mdata.split() #creates a list out of the relevant line of metadata
                                cfn = array[0] + '.pdf' #assigns the first item in the metadata list as the file name (should be the same as filecode)
                                cfnl = [cfn] #creates a list with just that one element, to compensate for changes due to new web delivery system
                                path = 'letters/' + cfn + '.aes' #the path to the file to be attached should be letters/[value of cfn].aes
                                if not os.path.isfile(path): #checks whether there is such a file
                                    no_such_file_handler(replyadr,cfn,log)
                                else:
                                    attach = [f_decrypt(path, key)] #assigns decrypted file as attachment
                                    maybepdf = StringIO.StringIO(attach[0]) #checks to make sure the file isn't corrupt
                                    try:
                                        PyPDF2.PdfFileReader(maybepdf)
                                    except PyPDF2.utils.PdfReadError:
                                        corrupt_file_handler(replyadr,cfn,log)
                                        maybepdf.close()
                                    else:
                                        maybepdf.close()
                                        rfn = array[1].replace('_', ' ') #assigns the items of the metadata list to variables; this is recommender's first name
                                        rln = array[2].replace('_', ' ') #recommender's last name
                                        afn = array[3].replace('_', ' ') #applicant's first name
                                        aln = array[4].replace('_', ' ') #applicant's last name
                                        aem = array[5] #applicant's email address
                                        failed = [] #creates an empty list for non-whitelisted addresses that will not receive attachment
                                        sentto = "" #creates an empty variable for whitelisted addresses that will receive attachment
                                        for match in matches:
                                            if ( key == 'B8NUTB85i' ): #allows for test deliveries of test letter file to any address
                                                delivery_handler(match,rfn,rln,afn,aln,attach,cfnl,log)
                                                sentto += match + ' ' #adds to the variable that contains whitelisted addresses that have been sent attachment
                                        for match in matches + [replyadr]: #checks each email address in the body and the reply-to address against the whitelist
                                            wl = io.open('static/whitelist.txt', 'r', encoding="utf-8")
                                            for line in wl:
                                                if ( match.lower() == line.rstrip().lower() and match not in sentto.strip().lower() ):
                                                        delivery_handler(match,rfn,rln,afn,aln,attach,cfnl,log)
                                                        sentto += match + ' ' #adds to the variable that contains whitelisted addresses that have been sent attachment
                                                else:
                                                    failed.append(match) #adds to the list of non-whitelisted addresses that have not been sent attachment
                                            wl.close()
                                        fsent = "" #creates an empty variable for...
                                        for miss in failed: #...deduplication and removal of reply-to address from the list of failed recipients
                                            if ( miss.lower() != replyadr.lower() and miss.lower() not in sentto.strip().lower() and miss.lower() not in fsent.strip().lower() ):
                                                fsent += miss + ' '
                                                log.write(u'Delivery failed to ' + miss + u'.\r\n')
                                        if sentto == "": #deals with cases where there were no whitelisted addresses
                                            not_whitelisted_handler(replyadr,log)
                                        else: #sends confirmations to the applicant and the reply-to address (if attachment was sent anywhere)
                                            applicant_confirmation_handler(aem,rfn,rln,afn,aln,cfn,sentto,fsent,log)
                                            if ( replyadr.lower() != aem.lower()):
                                               sender_confirmation_handler(replyadr,rfn,rln,afn,aln,cfn,sentto,fsent,log)
            log.write(u'End of log entry.\r\n')
            log.close()
            print 'Done.'
            return

#Listen to port 25 ( 0.0.0.0 can be replaced by the ip of your server but that will work with 0.0.0.0 )
server = MargySMTPServer((sys.argv[1], 25), None)

# Wait for incoming emails
asyncore.loop()
