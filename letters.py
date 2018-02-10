# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, send_from_directory, g
from flask.ext.mobility import Mobility
from flask.ext.mobility.decorators import mobile_template
from outgoing_email import EmailUtils
from encryption import f_encrypt, f_decrypt
import PyPDF2
import StringIO
import io, os, sys, re
import datetime
import os.path
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__, static_url_path='')
auth = HTTPBasicAuth()
Mobility(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 #sets max size of 16 MB for uploads

users = {}
fileloc = 'login'
with open(fileloc) as i:
     for line in i:
          (key, val) = line.split()
          users[key] = val

@app.route('/') #handles requests for http://margymail.com
def home():
    return render_template('home.html')

@app.route('/upload') #handles requests for http://margymail.com/upload
def newletter():
    return render_template('upload.html')

@app.route('/deliver') # handles requests for http://margymail.com/deliver
def deliver():
    return render_template('deliver.html')

@app.errorhandler(413) #renders error template for oversized files
def too_big(error):
    return render_template('toobig.html'), 413

@app.route('/instructions') #handles requests for http://margymail.com/instructions
def instructions():
    return render_template('quick.html')

@app.route('/detailed') #handles requests for Detailed Instructions from within http://margymail.com/instructions
def detailed():
    return render_template('detailed.html')

@app.route('/faq') #handles requests for How To... from within http://margymail.com/instructions
def questions():
    return render_template('faq.html')

@app.route('/whitelist') #handles requests for http://margymail.com/whitelist
def whitelist():
    with io.open('static/whitelist.txt', 'r', encoding="utf-8") as f: #gets the contents of whitelist.txt so they can be displayed
        data = f.read().replace('@', ' [at] ').replace('.', ' [dot] ')
    return render_template('whitelist.html',data=data)

@app.route('/thanks') #displays message of thanks to donors
def thanks():
    return render_template('thanks.html')

@app.route('/credits') #handles requests for http://margymail.com/credits
def credits():
    return render_template('credits.html')

@app.route('/unsubscribe', defaults={'email': ''})
@app.route('/unsubscribe/<email>') #handles requests for http://margymail.com/unsubscribe
def unsubscribe(email):
    return render_template('unsubscribe.html',email=email)

@app.route('/blastlist', defaults={'email': ''})
@app.route('/blastlist/<email>') #handles requests for http://margymail.com/blastlist
def blastlist(email):
    return render_template('blastlist.html',email=email)

@app.route('/storage/<path:path>') #URL handler for public storage directory
def storage(path):
    return send_from_directory('storage', path)

@auth.get_password #password protection for admin page
def get_pw(username):
    if username in users:
        return users.get(username)
    return None

@app.route('/admin') #admin only
@auth.login_required
def admin():
    return render_template('admin.html')

@app.route('/tail', methods=['POST']) #admin Only
def tail():
    if request.method == 'POST':
        fi = request.form['file']
        if os.path.isfile(fi):
            n = int(request.form['n'])
            le = io.open(fi, 'r', encoding='utf-8')
            taildata = le.read()[-n:]
            le.close()
        else:
            taildata = "No such file."
        return render_template('tail.html',taildata=taildata)

@app.route('/wladd', methods=['POST']) #adds addresses to whitelist (admin only, password protected)
def wladd():
    if request.method == 'POST':
        addr = request.form['addr'].lstrip().rstrip()
        f = io.open('static/whitelist.txt', 'a', encoding="utf-8")
        f.write(addr.decode('utf-8') + u'\r\n')
        f.close()
        return render_template('wladd.html')

@app.route('/unsub', methods=['POST']) #adds unsubscriber emails to unsubscriber list and removes from whitelist
def unsub():
    if request.method == 'POST':
        addr = request.form['addr'].lstrip().rstrip()
        f = io.open('unsubscribers.txt', 'a', encoding="utf-8")
        f.write(addr.decode('utf-8') + u'\r\n')
        f.close()
        f = io.open('static/whitelist.txt', 'r', encoding="utf-8")
        lines = f.readlines()
        f.close()
        f = io.open('static/whitelist.txt', 'w', encoding="utf-8")
        for line in lines:
            if addr not in line:
                f.write(line.decode('utf-8'))
        f.close()
        return render_template('unsubscribed.html',addr=addr)

@app.route('/blastaddrm', methods=['POST']) #adds/removes email addresses to/from email blast list
def add():
    if request.method == 'POST':
        if request.form['submit'] == 'Add':
            addr = request.form['addr'].lstrip().rstrip()
            f = io.open('blastlist.txt', 'a', encoding="utf-8")
            f.write(addr.decode('utf-8') + u'\r\n')
            f.close()
            return render_template('listadded.html',addr=addr)
        elif request.form['submit'] == 'Remove':
            addr = request.form['addr'].lstrip().rstrip()
            f = io.open('blastlist.txt', 'r', encoding="utf-8")
            lines = f.readlines()
            f.close()
            f = io.open('blastlist.txt', 'w', encoding="utf-8")
            for line in lines:
                if addr not in line:
                    f.write(line.decode('utf-8'))
            f.close()
            return render_template('listremoved.html',addr=addr)

@app.route('/addrequest') # handles requests for http://margymail.com/addrequest
def addrequest():
    return render_template('addrequest.html')

@app.route('/request', methods=['POST']) # sends requests for whitelist additions
def wlrequest():
    if request.method == 'POST':
        addr = request.form['addr'].lstrip().rstrip()
        ad = request.form['ad'].lstrip().rstrip()
        reply = request.form['reply'].lstrip().rstrip()
        EmailUtils.text_message('MARGY@margymail.com','faraci@gmail.com','Whitelist Addition Request',addr + '\r\n' + ad + '\r\n' + reply)
        return render_template('requested.html')

@app.route('/letter', methods=['POST']) # handles uploads
def upload_letter():
    if request.method == 'POST':
        rfn = request.form['rec_fname'].lstrip().rstrip() #assigns input text to variables; this is Recommender's First Name
        rln = request.form['rec_lname'].lstrip().rstrip() #Recommender's Last Name
        afn = request.form['app_fname'].lstrip().rstrip() #Applicant's First Name
        aln = request.form['app_lname'].lstrip().rstrip() #Applicant's Last Name
        aem = request.form['app_email'].lstrip().rstrip() #Applicant's Email Address
        aec = request.form['app_emailc'].lstrip().rstrip() #Applicant's Email Address (confirmed)
        note = request.form['app_note'] #Optional note to applicant
        rfncode = rfn.replace(" ", "_") #Replaces spaces with underscores in names
        rlncode = rln.replace(" ", "_")
        afncode = afn.replace(" ", "_")
        alncode = aln.replace(" ", "_")
        codename = alncode + rlncode #Assigns Applicant's Last Name and Recommender's Last Name as the fist part of the letter's file name
        d = io.open('metadata.txt', 'r', encoding="utf-8")
        num = 0
        for line in d: #checks whether there are other lines in the metadata with the same Last Names combination
            if codename.lower() == line.rstrip().lower()[:len(codename)]:
                num += 1
        if num != 0: #if there are n instances of this particular Last Name Combination in the metadata and n > 0, appends the codename with n+1.
            codename += str(num)
        codedfilename = 'letters/' + codename + ".pdf" #assigns the file a path: letters/[value of codename].pdf
        metadata = codename + ' ' + rfncode + ' ' + rlncode + ' ' + afncode + ' ' + alncode + ' ' + aem + '\r\n' #creates a line of metadata from all the above
        f = request.files['letter']
        if f.mimetype != 'application/pdf': #displays an error if the uploaded file is not a PDF
            return render_template('failure.html')
        else:
            if aem != aec: #displays an error if the email addresses do not match
                return render_template('mismatch.html')
            else:
                key = f_encrypt(codedfilename, f.read()) #encrypts the letter and assigns it a decryption key
                mailto = codename + '_' + key #creates a mailto code, concatenating the codename, an underscore, and the key
                a = io.open('metadata.txt', 'a', encoding="utf-8")
                a.write(metadata) #writes the metadata to metadata.txt
                a.close()
                txtbody = render_template('rec_confirm.txt',rfn=rfn,rln=rln,afn=afn,aln=aln,aem=aem,codename=mailto,note=note)
                htmlbody = render_template('rec_confirm.html',rfn=rfn,rln=rln,afn=afn,aln=aln,aem=aem,codename=mailto,note=note)
                EmailUtils.rich_message('MARGY@margymail.com',aem,'Letter Received',txtbody,htmlbody) #sends an email to the applicant with their mailto code
                savedas = codename + '.pdf'
                return render_template('success.html',aem=aem,codename=codename,savedas=savedas) #displays a success message to the uploader

@app.route('/delivery', methods=['POST']) # handles uploads
def delivery():
    if request.method == 'POST':
        now = datetime.datetime.now().strftime("%m.%d.%Y %H:%M:%S")
        log = io.open('httplog.txt', 'a', encoding="utf-8")
        log.write(u'\r\n' + now + u'\r\n')
        mc = []
        mc.append(request.form['mc0'].lstrip().rstrip())
        mc.append(request.form['mc1'].lstrip().rstrip())
        mc.append(request.form['mc2'].lstrip().rstrip())
        mc.append(request.form['mc3'].lstrip().rstrip())
        mc.append(request.form['mc4'].lstrip().rstrip())
        mc.append(request.form['mc5'].lstrip().rstrip())
        mc.append(request.form['mc6'].lstrip().rstrip())
        mc.append(request.form['mc7'].lstrip().rstrip())
        mc.append(request.form['mc8'].lstrip().rstrip())
        mc.append(request.form['mc9'].lstrip().rstrip())
        da = []
        da.append(request.form['del0'].lstrip().rstrip())
        da.append(request.form['del1'].lstrip().rstrip())
        da.append(request.form['del2'].lstrip().rstrip())
        da.append(request.form['del3'].lstrip().rstrip())
        da.append(request.form['del4'].lstrip().rstrip())
        da.append(request.form['del5'].lstrip().rstrip())
        da.append(request.form['del6'].lstrip().rstrip())
        da.append(request.form['del7'].lstrip().rstrip())
        da.append(request.form['del8'].lstrip().rstrip())
        da.append(request.form['del9'].lstrip().rstrip())
        addr = request.form['addr'].lstrip().rstrip().decode('utf-8')

        approved = []
        failed = []
        for address in da: #checks input addresses against whitelist
            if address != '':
                wl = io.open('static/whitelist.txt', 'r', encoding="utf-8")
                for line in wl:
                    if ( address.lower() == line.rstrip().lower() and address.lower() not in approved ):
                        approved.append(address) #adds to the list that contains whitelisted addresses
                if ( address.lower() not in approved and address.lower() not in failed ):
                    failed.append(address) #adds to the list of non-whitelisted addresses
                wl.close()

        unusable = []
        usable = []
        key = []
        err = 0
        for code in mc: #checks input mailto codes against metadata
            if code != '':
                metadata = io.open('metadata.txt', 'r', encoding="utf-8")
                for line in metadata:
                    if ( len(code) > 11 and code[:-10].lower() == line.rstrip().lower()[:len(code[:-10])] and line not in usable ):
                        usable.append(line)
                        key.append(code[-9:])
                if ( code[-9:] not in key and code not in unusable ):
                    unusable.append(code)
                    err = 1
                metadata.close()

        nofile = []
        corrupt = []
        attach = []
        data = []
        name = []
        i = 0
        for entry in usable:
            array = entry.split() #creates a list out of the relevant line of metadata
            cfn = array[0] + '.pdf' #assigns the first item in the metadata list as the file name (should be the same as filecode)
            path = 'letters/' + cfn + '.aes' #the path to the file to be attached should be letters/[value of cfn].aes
            if not os.path.isfile(path): #checks whether there is such a file
                nofile.append(cfn)
                key.remove(key[i])
                usable.remove(entry)
                err = 1
            else:
                attach = f_decrypt(path, key[i]) #assigns decrypted file as attachment
                maybepdf = StringIO.StringIO(attach) #checks to make sure the file isn't corrupt
                try:
                    PyPDF2.PdfFileReader(maybepdf)
                except PyPDF2.utils.PdfReadError:
                    corrupt.append(cfn)
                    usable.remove(entry)
                    key.remove(key[i])
                    maybepdf.close()
                    err = 1
                else:
                    data.append(attach)
                    name.append(cfn)
                    maybepdf.close()
            i += 1

        i = 0
        recsl = []
        recs = ''
        senttol = []
        sentto = ''
        applicant = ''
        aem = ''
        if ( usable and approved and err != 1 ):
            for address in approved:
                mto = address.decode('utf-8')
                for entry in usable:
                    array = entry.split()
                    rfn = array[1].replace('_', ' ').decode('utf-8') #assigns the items of the metadata list to variables; this is recommender's first name
                    rln = array[2].replace('_', ' ').decode('utf-8') #recommender's last name
                    rec = rfn + ' ' + rln
                    if rec not in recsl: recsl.append(rec)
                    afn = array[3].replace('_', ' ').decode('utf-8') #applicant's first name
                    aln = array[4].replace('_', ' ').decode('utf-8') #applicant's last name
                    applicant = afn + ' ' + aln
                    aem = array[5].decode('utf-8') #applicant's email address
                recs = '; '.join(recsl)
                subject = 'Recommendation Letters for ' + applicant
                toedutxt = render_template('delivery.txt',recs=recs,app=applicant,email=mto)
                toedu = render_template('delivery.html',recs=recs,app=applicant,email=mto)
                senttol.append(mto)
                EmailUtils.rich_message('MARGY@margymail.com',mto,subject,toedutxt,toedu,data,name)
                i += 1
            if approved and usable:
                files = '; '.join(name)
                sentto = '; '.join(senttol)
                log.write(str(len(usable)) + u' deliveries made to: ' + sentto +  u'\r\n')
                toapptxt = render_template('del_confirm.txt',recs=recs,app=applicant,cfn=files,sentto=sentto,failed='')
                toapp = render_template('del_confirm.html',recs=recs,app=applicant,cfn=files,sentto=sentto,failed='')
                EmailUtils.rich_message('MARGY@margymail.com',aem,'Letter Delivery Confirmation',toapptxt,toapp)
                if ( aem != addr and addr != '' ):
                    EmailUtils.rich_message('MARGY@margymail.com',addr,'Letter Delivery Confirmation',toapptxt,toapp)

        nf = '; '.join(nofile).decode('utf-8')
        if nf != '':
            log.write(u'Missing file: ' + nf + u'\r\n')

        nwl = '; '.join(failed).decode('utf-8')
        if nwl != '':
            log.write(u'Non-whitelisted: ' + nwl + u'\r\n')

        cor = '; '.join(corrupt).decode('utf-8')
        if cor != '':
            log.write(u'Corrupt: ' + cor + u'\r\n')

        nmd = '; '.join(unusable).decode('utf-8')
        if nmd != '':
            if 'margymail' in nmd:
                log.write(u'Missing metadata: anonymized @margymail input\r\n')
            else:
                log.write(u'Missing metadata: ' + nmd + u'\r\n')
        log.close()
        return render_template('results.html',recs=recs,app=applicant,corrupt=corrupt,failed=nwl,nmd=nmd,nf=nf,sentto=sentto,aem=aem,addr=addr)
