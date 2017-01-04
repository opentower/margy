#Welcome to MARGY Beta Testing!

MARGY is a **FREE** service for managing confidential letters of recommendation on the academic job market. Before we officially launch the system, we want to fix as many bugs as possible, and make MARGY as user-friendly as possible. To that end, please consider participating in the beta test. Explore the [website](http://margymail.com), play with the upload system, add your email to the whitelist and use the system to send yourself files. Any feedback on the design or notes on functionality would be greatly appreciated. If you are a coder, you can also check out our source code on [GitHub](https://github.com/davidfaraci/margy).

For bugs/specific issues, please create an "Issue" on GitHub. Go to [https://github.com/davidfaraci/margy/issues](https://github.com/davidfaraci/margy/issues) and click "New Issue."

For comments and general suggestions (or if you find a bug but would prefer not to deal with the Issue system), send an email to [admin@margymail.com](mailto:admin@margymail.com).


-----


##How to Read the Source Code

If you're interested in understanding how MARGY works, you can view the source code here on GitHub. The following is a brief overview of what you'll find here. The two main files, `letters.py` and `server.py` have been heavily commented to ease understanding for those interested but without much relevant experience.

###GitHub Contents
- `static (folder)` contains files used by all parts of the site, such as logos and CSS stylesheets, as well as the whitelist
- `templates (folder)` contains the html templates for the different site pages as well as the various emails MARGY sends
- `.gitignore` tells the system which files not to share publicly (e.g., the folder with all the letters in it!)
- `LICENSE.txt` contains a statement of MARGY's copyright
- `README.md` contains this README
- `encryption.py` contains the functions `letters.py` uses to encrypt files during upload and `server.py` uses to decrypt files for delivery
- `letters.py` contains the code for the MARGY website (more below)
- `outgoing_email.py` contains the functions that `server.py` uses to send email
- `server.py` contains the code for the MARGY email system (more below)


####LETTERS.PY
`letters.py` controls what happens when someone visits any page on the MARGY site. It is based on [Flask](http://flask.pocoo.org/), a Python web development system. Most of what it does is take URL requests and deliver templates. The core page of the MARGY site is the `index.html` template, which contains the menu and the MARGY title. Each of the full pages you see adds to `index.html` with an extension template, and these extension templates are rendered by `letters.py`. For example

```
@app.route('/upload')
def newletter():
    return render_template('upload.html')
```

says that when someone goes to margymail.com/upload, the system should render the `upload.html` template (which is an extension of the `index.html` template). Most of `letters.py` is just short bits like this. The exception is `@app.route` for `/letter`, which controls uploading (when someone clicks Submit on margymail.com/upload, it triggers `/letter`). It takes the information provided by the uploader and adds it to `metadata.txt` (not public). It then creates a unique file name for the letter, encrypts it using functions from `encryption.py`, and saves it to the letters folder (also not public). It then renders appropriate templates (e.g., saying that a letter has been successfully uploaded).


####SERVER.PY
`server.py` controls what happens when an email is sent to any @margymail.com address. If you look at the file, after some initial imports and definitions, you'll see a series of email handlers. These are functions that the main function, `process_message`, uses to send the right email for the right context.

When an email comes in, `process_message` does the following:

1. Reads the email (including body and headers) and saves that information for future use.
2. Checks the body of the message for email addresses.
3. If the email is directed to abuse@, postmaster@ or admin@ or MARGY@margymail.com, it forwards it to me.
4. Checks whether the system has metadata associated with the incoming mailto code. If not, it sends an error reply.
5. Decrypts the file associated with that metadata (using the key found in the mailto code) and flags it for attachment.
6. Checks the email addresses from the incoming email against `whitelist.txt`. If there are no matches, it sends an error reply.
7. Sends an email with the decrypted letter as an attachment to each whitelisted address.
8. Sends a confirmation email to the applicant and the reply-to address (if different).
