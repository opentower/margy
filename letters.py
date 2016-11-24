from flask import Flask, render_template, request, g
from flask.ext.mobility import Mobility
from flask.ext.mobility.decorators import mobile_template
from outgoing_email import EmailUtils
import magic, os, sys, re

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
def about():
    return render_template('instructions.html')

@app.route('/whitelist')
def whitelist():
    with open('static/whitelist.txt', 'r') as f:
        data = f.read()
    return render_template('whitelist.html',data=data)

@app.route('/donate')
def donate():
    return render_template('donate.html')

@app.route('/credits')
def credits():
    return render_template('credits.html')

@app.route('/letter', methods=['POST'])
def upload_letter():
    if request.method == 'POST':
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
        f.save(codedfilename)
        m = magic.open(magic.MAGIC_MIME)
        m.load()
        if m.file(codedfilename) == 'application/pdf; charset=binary':
            if aem != aec:
                return render_template('mismatch.html')
            else:
                a = open('metadata.txt', 'a')
                a.write(metadata)
                a.close()
                htmlbody = render_template('rec_confirm.html',rfn=rfn,rln=rln,afn=afn,aln=aln,codename=codename)
                body = 'Dear ' + afn + ' ' + aln + ',' + '\r\n' + '\r\n' + 'MARGY has received a confidential letter of recommendation for you from ' + rfn + ' ' + rln + '. ' + 'To have the letter delivered to {email addresses}, send an email to ' + codename + '@margymail.com' + ' with {email addresses} in the email body. For more detailed instructions, visit http://margymail.com/instructions. If you have further questions, please direct them to admin@margybeta.davidfaraci.com.' + '\r\n' + '\r\n' + 'MARGY'
                EmailUtils.rich_message('MARGY@margy.davidfaraci.com',aem,'Letter Received',body,htmlbody)
                print "boo"
                return render_template('success.html',aem=aem,codename=codename)
        else:
            os.remove(codedfilename)
            return render_template('failure.html')
