# -*- coding: utf-8 -*-
import smtplib
import email
import re
from email import charset
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

charset.add_charset('utf-8',charset.SHORTEST,charset.QP)

class EmailUtils:
    email_pattern = re.compile('([a-zA-Z0-9])+([a-zA-Z0-9\._-])*@([a-zA-Z0-9_-])+([a-zA-Z0-9\._-]+)+')
    @staticmethod
    def forward_message(data, redirectto):
        from_adr='MARGY@margymail.com'
#      Forward a message (we change the From tag in the email headers wich I guess is not perfect, I'm not an email expert)
        msg=email.message_from_string(data)
        try:
            msg.add_header('Resent-from', from_adr);
#            msg.replace_header('Subject', '[DI] '  + msg['subject'])
        except KeyError:
            pass
#      Note we are usng port 6625 here as we've changed the Postfix port
        s = smtplib.SMTP('localhost','6625')
        s.sendmail(from_adr, redirectto, msg.as_string())
        s.quit()
        return

    @staticmethod
    def text_message(mfrom,to,topic,body):
#      Send an email with a simple text message
        msg=MIMEText(body,'plain','utf-8');
        msg['Subject'] = topic
        msg['From'] = mfrom
        msg['To'] = to
#      Note we are usng port 6625 here as we've changed the Postfix port
        s = smtplib.SMTP('localhost','6625')
        s.sendmail(mfrom, to, msg.as_string())
        s.quit()
        return

    @staticmethod
    def rich_message(mfrom,to,topic,plain,html=None,data=None,name=None):
#      Send an email with a simple text message
        ptpart = MIMEText(plain,'plain','utf-8')
        if html:
            body = MIMEMultipart('alternative')
            htmlpart = MIMEText(html,'html','utf-8')
            body.attach(ptpart)
            body.attach(htmlpart)
            if data:
                msg=MIMEMultipart('mixed')
                msg['Subject'] = topic
                msg['From'] = mfrom
                msg['To'] = to
                msg['List-Unsubscribe'] = '<mailto:admin@margymail.com>,<https://margymail.com/unsubscribe' + to + '>'
                msg.attach(body)
                pdf=MIMEApplication(data,'pdf')
                if name: pdf.add_header('Content-Disposition','attachment',filename=name)
                else: pdf.add_header('Content-Disposition','attachment')
                msg.attach(pdf)
                s = smtplib.SMTP('localhost','6625')
                s.sendmail(mfrom, to, msg.as_string())
                s.quit()
                return
            else:
                body['Subject'] = topic
                body['From'] = mfrom
                body['To'] = to
                body['List-Unsubscribe'] = '<mailto:admin@margymail.com>,<https://margymail.com/unsubscribe' + to + '>'
                s = smtplib.SMTP('localhost','6625')
                s.sendmail(mfrom, to, body.as_string())
                s.quit()
                return
        else:
            if data:
                msg=MIMEMultipart('mixed')
                msg['Subject'] = topic
                msg['From'] = mfrom
                msg['To'] = to
                msg['List-Unsubscribe'] = '<mailto:admin@margymail.com>,<https://margymail.com/unsubscribe' + to + '>'
                msg.attach(ptpart)
                pdf=MIMEApplication(data,'pdf')
                if name: pdf.add_header('Content-Disposition','attachment',filename=name)
                else: pdf.add_header('Content-Disposition','attachment')
                msg.attach(pdf)
                s = smtplib.SMTP('localhost','6625')
                s.sendmail(mfrom, to, msg.as_string())
                s.quit()
                return
            else:
                ptpart['Subject'] = topic
                ptpart['From'] = mfrom
                ptpart['To'] = to
                ptpart['List-Unsubscribe'] = '<mailto:admin@margymail.com>,<https://margymail.com/unsubscribe' + to + '>'
                s = smtplib.SMTP('localhost','6625')
                s.sendmail(mfrom, to, ptpart.as_string())
                s.quit()
                return
