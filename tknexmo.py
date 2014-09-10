#!/usr/bin/env python
# -*- coding: utf-8 -*-
import platform
import json
import urllib
import urllib2
import time
import sys
import os
import base64

# check for tkinter
try:
    import Tkinter as gui
    import tkMessageBox as msg
except ImportError:
    sys.exit('Runtime import error for Tkinter')


# --------------------- #
# Configuration options #
# --------------------- #
class Config:

    default_from = platform.node()
    credentials_file = 'credentials.db'
    credentials_dict = {}

    app_debug = True

    contacts_file = 'contacts.db'
    contacts_dict = {}

# ---------------- #
# Widget utilities #
# ---------------- #
class WindowUtil:

    @staticmethod
    def center(window):

        window.update_idletasks()
        size_x = window.winfo_width()
        size_y = window.winfo_height()

        screen_x = window.winfo_screenwidth()
        screen_y = window.winfo_screenheight()

        offset_x = (screen_x - size_x) / 2
        offset_y = (screen_y - size_y) / 2

        geometry = (size_x, size_y, offset_x, offset_y)

        window.geometry('%dx%d+%d+%d' % geometry)

# ------------- #
# Logging class #
# ------------- #
class Log:

    now = time.strftime('%Y-%m-%d %H:%M:S')

    @staticmethod
    def info(msg):

        if not Config.app_debug:
            return

        sys.stdout.write('[%s]: %s\n' % (Log.now, msg.strip()))

    @staticmethod
    def fatal(msg):

        sys.stdout.write('[%s]: %s\n' % (Log.now, msg.strip()))
        sys.exit(1)

# ------------------- #
# Nexmo message class #
# ------------------- #
class Nexmo:

    def __init__(self, sms_from, sms_to, sms_txt):

        nexmo_data = urllib.urlencode({
            'api_key':      Config.credentials_dict['key'],
            'api_secret':   Config.credentials_dict['secret'],
            'from':         sms_from,
            'to':           sms_to,
            'text':         sms_txt,
            'type':         'unicode',
        })

        self.sms_to = sms_to
        self.nexmo_url = 'https://rest.nexmo.com/sms/json?%s' % nexmo_data


    def send(self):

        Log.info('Sending SMS to %s...' % self.sms_to)
        nexmo_response = json.loads(urllib2.urlopen(self.nexmo_url).read())
        return nexmo_response

# -------------- #
# Widget actions #
# -------------- #
class Action:


    # CREDENTIALS
    @staticmethod
    def credentials_save(key, secret):

        Log.info('Credentials saving')
        Config.credentials_dict = {
            'key': key,
            'secret': secret
        }

        open(Config.credentials_file, 'w').write(base64.b64encode(
            json.dumps(Config.credentials_dict, indent=4)
        ))

    @staticmethod
    def credentials_load():

        Log.info('Credentials loading')
        try:
            Config.credentials_dict = json.loads(base64.b64decode(
                open(Config.credentials_file, 'r').read()
            ))
        except IOError:
            pass

    # SMS
    @staticmethod
    def sms_conf():

        Log.info('ConfWindow starting')
        conf = ConfWindow(app)
        conf.title("Configure")
        WindowUtil.center(conf)


    @staticmethod
    def sms_send():

        Log.info("SMS validating")

        msg_err = None

        # collect form data
        sms_from = app.entry_from.get()
        sms_to = app.entry_to.get()
        sms_txt = app.entry_txt.get(1.0, gui.END).strip()

        sms_txt = sms_txt.encode('utf-8')
        Log.info(sms_txt)

        # validate form data
        if not sms_from:
            msg_err = 'SMS sender cannot be empty'
        elif not sms_to:
            msg_err = 'SMS recipient cannot be empty'
        elif not sms_txt:
            msg_err = 'SMS text cannot be empty'
            
        if msg_err:
            msg.showinfo(title='Error', message=msg_err)
            Log.info(msg_err)
            return
            
        # try to send
        Log.info('Connecting to Nexmo service')
        try:
            response = Nexmo(sms_from, sms_to, sms_txt).send()
        except KeyError:
            msg_err = 'You need to configure your Nexmo key and secret'
            msg.showinfo(title='Error', message=msg_err)
            return

        if response['messages'][0]['status'] == '0':
            msg_ok = u'SMS sent to %s.\n' % response['messages'][0]['to']
            msg_ok += u'Account balance now %s€' % response['messages'][0]['remaining-balance']
            msg.showinfo(title="Success", message=msg_ok)
        else:
            msg_err = 'Server response:\n%s' % str(response)
            msg.showinfo(title="Sending SMS failed", message=msg_err)

        
        # if this is an already known contact
        # we don't wanna save it again
        if sms_to in Config.contacts_dict.values():
            Log.info('Number %s already exists. Not saving again.' % sms_to)
            return

        # build a tmp name and reload contacts
        tmp_name = 'ContactName_%d' % len(Config.contacts_dict)
        Config.contacts_dict[tmp_name] = sms_to

        Action.contacts_save()
        Action.contacts_load()

    @staticmethod
    def sms_clear():

        Log.info("SMS clearing")
        app.entry_from.delete(0, gui.END)
        app.entry_to.delete(0, gui.END)
        app.entry_txt.delete(0.0, gui.END)

    @staticmethod
    def contacts_save():

        Log.info("Contacts saving")
        open(Config.contacts_file, 'w').write(json.dumps(Config.contacts_dict, indent=4))

    @staticmethod
    def contacts_load():

        Log.info("Contacts loading")
        try:
            Config.contacts_dict = json.loads(open(Config.contacts_file, 'r').read())
        except IOError:
            pass

        app.contacts.delete(0, gui.END)
        for name, phone in Config.contacts_dict.items():
                
            app.contacts.insert(gui.END, name)


    @staticmethod
    def contacts_delete():

        selected = app.contacts.curselection()
        if not selected:
            return
        contact = app.contacts.get(selected)

        Log.info('Deleting contact %s' % contact)
        app.contacts.delete(selected)
        del Config.contacts_dict[contact]
            
        Action.contacts_save()
        Action.sms_clear()

    @staticmethod
    def contacts_selected(event):

        selected = app.contacts.curselection()
        if not selected:
            return
        contact = app.contacts.get(selected)

        Log.info('Selected %s' % contact)
        app.entry_to.delete(0, gui.END)
        app.entry_to.insert(0, Config.contacts_dict[contact])
        

    @staticmethod
    def contacts_edit():

        selected = app.contacts.curselection()
        if not selected:
            return
        contact = app.contacts.get(selected)

        num = Config.contacts_dict[contact]
        edit = ContactsEditWindow(contact, num, app)
        edit.title('Edit contact')


# -------------------- #
# Contacts edit window #
# -------------------- #
class ContactsEditWindow(gui.Toplevel):

    def __init__(self, name, num, master=None):
        gui.Toplevel.__init__(self, master)
        self.name = name
        self.num = num
        self.widgets()

    def save(self):
        
        new_name = self.edit_name.get()
        new_num  = self.edit_num.get()
        Log.info('Saving edited contact %s as %s' % (new_name, new_num))

        del Config.contacts_dict[self.name]
        Config.contacts_dict[new_name] = new_num
        Action.contacts_save()
        Action.contacts_load()
        self.destroy()
        
        


    def widgets(self):

        # TOP FRAME
        lf_top = gui.LabelFrame(self, text='Edit contact')
        lf_top.pack(side=gui.TOP)

        lbl_name = gui.Label(lf_top, text='Name:')
        lbl_num  = gui.Label(lf_top, text='Number:')

        edit_name = gui.Entry(lf_top)
        edit_num  = gui.Entry(lf_top)

        self.edit_name = edit_name
        self.edit_num = edit_num

        edit_name.insert(0, self.name)
        edit_num.insert(0, self.num)

        lbl_name.grid(row=0, column=0)
        edit_name.grid(row=0, column=1)

        lbl_num.grid(row=1, column=0)
        edit_num.grid(row=1, column=1)

        # BOTTOM FRAME
        frm_bottom = gui.Frame(self)
        frm_bottom.pack(side=gui.BOTTOM, fill=gui.X)

        btn_save = gui.Button(frm_bottom, text='Save', command=self.save)
        btn_cancel = gui.Button(frm_bottom, text='Cancel', command=self.destroy)

        btn_save.pack(side=gui.LEFT, fill=gui.X, expand=True)
        btn_cancel.pack(side=gui.RIGHT, fill=gui.X, expand=True)

        
# -------------------- #
# Configuration Window #
# -------------------- #
class ConfWindow(gui.Toplevel):

    def __init__(self, master=None):
        gui.Toplevel.__init__(self, master)
        self.widgets()

        if Config.credentials_dict:
            
            self.input_key.set(Config.credentials_dict['key'])
            self.input_secret.set(Config.credentials_dict['secret'])

    def save(self):

        key = self.input_key.get()
        secret = self.input_secret.get()

        if not key or not secret:
            msg.showinfo(title='Error', message='Cannot accept empty key or secret')
            return

        Action.credentials_save(key, secret)
        self.destroy()
            
    def clear(self):

        Log.info('Clearing credentials form')
        self.input_key.set('')
        self.input_secret.set('')

        try:
            os.remove(Config.credentials_file)
            Config.credentials_dict = {}
        except: pass

    def widgets(self):

        input_key = gui.StringVar()
        input_secret = gui.StringVar()

        self.input_key = input_key
        self.input_secret = input_secret

        lf = gui.LabelFrame(self, text="Nexmo configuration")
        lf.pack(side=gui.TOP, padx=5, pady=5)

        lbl_key = gui.Label(lf, text="Nexmo key:")
        lbl_secret = gui.Label(lf, text="Nexmo secret:")

        entry_key = gui.Entry(lf, textvariable=input_key, width=8)
        entry_secret = gui.Entry(lf, textvariable=input_secret, width=8, show="*")

        lbl_key.grid(row=0, column=0, sticky=gui.W)
        entry_key.grid(row=0, column=1)

        lbl_secret.grid(row=1, column=0, sticky=gui.W)
        entry_secret.grid(row=1, column=1)

        # buttons
        lf2 = gui.Frame(self)
        lf2.pack(fill=gui.X, expand=True, padx=5, pady=5)
        btn_save = gui.Button(lf2, text="Save", command=self.save)
        btn_clear = gui.Button(lf2, text="Clear", command=self.clear)
        btn_close = gui.Button(lf2, text="Close", command=self.destroy)

        btn_save.pack(side=gui.LEFT, fill=gui.X, expand=True)
        btn_clear.pack(side=gui.LEFT, fill=gui.X, expand=True)
        btn_close.pack(side=gui.LEFT, fill=gui.X, expand=True)

# ----------- #
# Main window #
# ----------- #
class MainWindow(gui.Frame):

    def __init__(self, master=None):
        gui.Frame.__init__(self, master)
        self.pack()
        self.widgets()


    def widgets(self):

        # contacts: labelframe
        lf_contacts = gui.LabelFrame(self, text="Contacts")
        lf_contacts.pack(side=gui.LEFT, anchor=gui.NW, padx=5, pady=5)

        # contacts: listbox
        contacts = gui.Listbox(lf_contacts, height=12)
        self.contacts = contacts

        contacts.pack(side=gui.TOP)
        contacts.bind('<<ListboxSelect>>', Action.contacts_selected)

        # contacts: buttons
        btn_del = gui.Button(lf_contacts, text="Delete", command=Action.contacts_delete)
        btn_del.pack(side=gui.RIGHT, fill=gui.BOTH, expand=1)

        btn_edit = gui.Button(lf_contacts, text="Edit", command=Action.contacts_edit)
        btn_edit.pack(side=gui.RIGHT, fill=gui.BOTH, expand=1)

        # sms: labelframe
        lf_sms = gui.LabelFrame(self, text="SMS")
        lf_sms.pack(side=gui.TOP, anchor=gui.NW, fill=gui.BOTH, expand=True, padx=5, pady=5)

        # sms: from
        lbl_from = gui.Label(lf_sms, text="From:")
        lbl_from.grid(row=0, column=0, padx=10, pady=5, sticky=gui.W)

        entry_from = gui.Entry(lf_sms, width=11)
        entry_from.grid(row=0, column=1, padx=10, pady=5, sticky=gui.W)
        entry_from.insert(0, Config.default_from)
        self.entry_from = entry_from
        
        # sms: to
        lbl_to = gui.Label(lf_sms, text="To:")
        lbl_to.grid(row=1, column=0, padx=10, pady=5, sticky=gui.W)

        entry_to = gui.Entry(lf_sms, width=16)
        entry_to.grid(row=1, column=1, padx=10, pady=5, sticky=gui.W)
        self.entry_to = entry_to

        # sms: text
        lbl_txt= gui.Label(lf_sms, text="Text:")
        lbl_txt.grid(row=2, column=0, padx=10, pady=5, sticky=gui.N)

        entry_txt = gui.Text(lf_sms, width=37, height=5)
        entry_txt.grid(row=2, column=1, padx=10, pady=5)
        self.entry_txt = entry_txt

        # sms: buttons
        lf_controls = gui.LabelFrame(self, text="Controls")
        lf_controls.pack(side=gui.RIGHT, anchor=gui.SW, fill=gui.X, expand=True, padx=5, pady=5)

        btn_conf = gui.Button(lf_controls, text="Configure", command=Action.sms_conf)
        btn_send = gui.Button(lf_controls, text="Send", command=Action.sms_send)
        btn_clear = gui.Button(lf_controls, text="Clear", command=Action.sms_clear)
        btn_quit = gui.Button(lf_controls, text="Quit", command=root.quit)

        btn_conf.pack(side=gui.LEFT, fill=gui.X, anchor=gui.S, expand=True)
        btn_send.pack(side=gui.LEFT, fill=gui.X, anchor=gui.S, expand=True)
        btn_clear.pack(side=gui.LEFT, fill=gui.X, anchor=gui.S, expand=True)
        btn_quit.pack(side=gui.LEFT, fill=gui.X, anchor=gui.S, expand=True)


# ---------- #
# Main stuff # 
# ---------- #
os.umask(077)
Log.info('tkNexmo starting')


# init: screen
root = gui.Tk()
root.resizable(0, 0)
root.title("Nexmo SMS")
root.option_add('*Font', 'courier')

# init: main window
app = MainWindow(root)

# init: data
Action.credentials_load()
Action.contacts_load()

app.mainloop()
Log.info("tkNexmo exiting")
