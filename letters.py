from flask import Flask, render_template, request, send_from_directory, g
from flask.ext.mobility import Mobility
from flask.ext.mobility.decorators import mobile_template
from flask_httpauth import HTTPBasicAuth
from outgoing_email import EmailUtils
from encryption import f_encrypt
import os, sys, re

app = Flask(__name__, static_url_path='')
auth = HTTPBasicAuth()
Mobility(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 #sets max size of 16 MB for uploads

users = {}
fileloc = '/home/margy/login'
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

@app.errorhandler(413) #renders error template for oversized files
def too_big(error):
    return render_template('toobig.html'), 413

@app.route('/instructions') #handles requests for http://margymail.com/instructions
def instructions():
    return render_template('quick.html')

@app.route('/detailed') #handles requests for Detailed Instructions from within http://margymail.com/instructions
def detailed():
    return render_template('detailed.html')

@app.route('/howto') #handles requests for How To... from within http://margymail.com/instructions
def questions():
    return render_template('howto.html')

@app.route('/confidentiality') #handles requests for http://margymail.com/confidentiality
def whitelist():
    with open('static/whitelist.txt', 'r') as f: #gets the contents of whitelist.txt so they can be displayed
        data = f.read()
    return render_template('confidentiality.html',data=data)

@app.route('/donate') #handles requests for http://margymail.com/donate
def donate():
    return render_template('donate.html')

@app.route('/thanks') #displays message of thanks to donors
def thanks():
    return render_template('thanks.html')

@app.route('/credits') #handles requests for http://margymail.com/credits
def credits():
    return render_template('credits.html')

@app.route('/storage/<path:path>') #URL handler for public storage directory
def storage(path):
    return send_from_directory('storage', path)

@auth.get_password #password protection for private storage directory
def get_pw(username):
    if username in users:
        return users.get(username)
    return None

@app.route('/private/<path:path>') #URL handler for private storage directory
@auth.login_required
def private(path):
    return send_from_directory('private', path)

@app.route('/letter', methods=['POST'])
def upload_letter():
    if request.method == 'POST':
        rfn = request.form['rec_fname'].lstrip().rstrip() #assigns input text to variables; this is Recommender's First Name
        rln = request.form['rec_lname'].lstrip().rstrip() #Recommender's Last Name
        afn = request.form['app_fname'].lstrip().rstrip() #Applicant's First Name
        aln = request.form['app_lname'].lstrip().rstrip() #Applicant's Last Name
        aem = request.form['app_email'].lstrip().rstrip() #Applicant's Email Address
        aec = request.form['app_emailc'].lstrip().rstrip() #Applicant's Email Address (confirmed)
        rfncode = rfn.replace(" ", "_") #Replaces spaces with underscores in names
        rlncode = rln.replace(" ", "_")
        afncode = afn.replace(" ", "_")
        alncode = aln.replace(" ", "_")
        codename = aln + rln #Assigns Applicant's Last Name and Recommender's Last Name as the fist part of the letter's file name
        d = open('metadata.txt', 'r')
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
                a = open('metadata.txt', 'a')
                a.write(metadata) #writes the metadata to metadata.txt
                a.close()
                txtbody = render_template('rec_confirm.txt',rfn=rfn,rln=rln,afn=afn,aln=aln,codename=mailto)
                htmlbody = render_template('rec_confirm.html',rfn=rfn,rln=rln,afn=afn,aln=aln,codename=mailto)
                EmailUtils.rich_message('MARGY@margymail.com',aem,'Letter Received',txtbody,htmlbody) #sends an email to the applicant with their mailto code
                return render_template('success.html',aem=aem,codename=codename) #displays a success message to the uploader
