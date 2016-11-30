from flask import Flask, render_template, request, g
from flask.ext.mobility import Mobility
from flask.ext.mobility.decorators import mobile_template
from outgoing_email import EmailUtils
from encryption import f_encrypt
import os, sys, re

app = Flask(__name__)
Mobility(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/upload')
def newletter():
    return render_template('upload.html')

@app.errorhandler(413)
def too_big(error):
    return render_template('toobig.html'), 413

@app.route('/instructions')
def instructions():
    return render_template('quick.html')

@app.route('/detailed')
def detailed():
    return render_template('detailed.html')

@app.route('/howto')
def questions():
    return render_template('howto.html')

@app.route('/confidentiality')
def whitelist():
    with open('static/whitelist.txt', 'r') as f:
        data = f.read()
    return render_template('confidentiality.html',data=data)

@app.route('/donate')
def donate():
    return render_template('donate.html')

@app.route('/thanks')
def thanks():
    return render_template('thanks.html')

@app.route('/credits')
def credits():
    return render_template('credits.html')

@app.route('/letter', methods=['POST'])
def upload_letter():
    if request.method == 'POST':
        render_template('progress.html')
        rfn = request.form['rec_fname'].lstrip().rstrip()
        rln = request.form['rec_lname'].lstrip().rstrip()
        afn = request.form['app_fname'].lstrip().rstrip()
        aln = request.form['app_lname'].lstrip().rstrip()
        aem = request.form['app_email'].lstrip().rstrip()
        aec = request.form['app_emailc'].lstrip().rstrip()
        rfncode = rfn.replace(" ", "_")
        rlncode = rln.replace(" ", "_")
        afncode = afn.replace(" ", "_")
        alncode = aln.replace(" ", "_")
        codename = aln + rln
        d = open('metadata.txt', 'r')
        num = 0
        for line in d:
            if codename.lower() == line.rstrip().lower()[:len(codename)]:
                num += 1
        if num != 0:
            codename += str(num)
        codedfilename = '/home/dev/LettersC-Flask/letters/' + codename + ".pdf"
        metadata = codename + ' ' + rfncode + ' ' + rlncode + ' ' + afncode + ' ' + alncode + ' ' + aem + '\r\n'
        f = request.files['letter']
        if f.mimetype != 'application/pdf':
            return render_template('failure.html')
        else:
            if aem != aec:
                return render_template('mismatch.html')
            else:
                key = f_encrypt(codedfilename, f.read())
                mailto = codename + '_' + key
                a = open('metadata.txt', 'a')
                a.write(metadata)
                a.close()
                txtbody = render_template('rec_confirm.txt',rfn=rfn,rln=rln,afn=afn,aln=aln,codename=mailto)
                htmlbody = render_template('rec_confirm.html',rfn=rfn,rln=rln,afn=afn,aln=aln,codename=mailto)
                EmailUtils.rich_message('MARGY@margymail.com',aem,'Letter Received',txtbody,htmlbody)
                print "boo"
                return render_template('success.html',aem=aem,codename=codename)
