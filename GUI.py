from mttkinter import mtTkinter as tk
import httplib
import time
from datetime import datetime
import requests
from threading import Thread
import sys
import logging
import webbrowser

# Global Variables
info = "Welcome to AutoLogin_v1.0\n\n" \
       "_________________________\n\n" \
       "Please Select a device..."
attempts = 0
user_list = []
pass_list = []
animation = ["Checking for devices   ", "Checking for devices.  ", "Checking for devices.. ", "Checking for devices..."]
devices = []
current_device = 0
dev_index = 0
dev_dic = {}
server = ""
blacklist = set()
output_ready = "0"

# Logging setup for gui
myFormat = '%(asctime)s - Message: %(message)s'
logging.basicConfig(format=myFormat, datefmt='%m/%d/%Y %I:%M:%S %p', filename='gui.log', level=logging.DEBUG)


class Device(object):
    """
    Class for a device to hold the variables and functions for a device
    """
    serial = ""
    index = 0
    info = ""

    def __init__(self, serial, index):
        self.serial = serial
        self.index = index

    def getserial(self):
        return self.serial

    def getindex(self):
        return self.index


def helpaction():
    """
    Called when the help button is pressed on the gui
    Displays any help information onto the screen
    """
    help = "If you are having issues pleae contact a member \n" \
           "of the 2017 Vistronix intern team \n\n" \
           "____________________________________________\n" \
           "Email: ******************\n" \
           "Phone: ******************"
    updatescreen(help)


def clearall():
    """
    Clears the display on the gui when the clear button is pressed
    :return:
    """
    devices[current_device].info = ""
    updatescreen("")


def deviceinfo():
    """
    Gets the device info from the current selected device
    :return: Creates a new window for the device info
    """
    serial = devices[current_device].serial
    global server
    conn = httplib.HTTPConnection(server.strip() + ":80")
    conn.request("GET", "/device_info/" + serial)
    r1 = conn.getresponse()
    data = r1.read()
    data = data[1:-1]
    toplevel = tk.Toplevel()
    label1 = tk.Label(toplevel, text="Device info for serial: " + serial, height=0, width=100)
    label1.pack()
    label2 = tk.Label(toplevel, text=data, height=0, width=100)
    label2.pack()


def cleardevices():
    """
    Refreshes the device list
    """
    global devices
    global current_device
    global dev_index
    global dev_dic
    global blacklist
    global lb
    lb.delete(0, tk.END)
    devices = []
    current_device = 0
    dev_index = 0
    dev_dic = {}
    blacklist = set()
    # Connects living devices back
    collecteddevices()


def clearlog():
    """
    Clears the server log
    """
    global server
    requests.post("http://" + server + ":80/clear_log")
    logging.info("Logs were just cleared at: " + datetime.now())
    print "Log cleared"


def geolocation():
    """
    Opens a new browser with Geolocation in it
    """
    webbrowser.open("http://ec2-54-208-112-65.compute-1.amazonaws.com/map")
    logging.info("Geolocation webpage opened")

def collecteddevices():
    """
    Connects the living devices from the server into the gui
    Displays the devices on the left device list
    """
    global server
    conn = httplib.HTTPConnection(server.strip() + ":80")
    conn.request("GET", "/collect_device_serials")
    r1 = conn.getresponse()
    my_serials = r1.read()
    my_serials = my_serials[:-1]
    serials_list = my_serials.split(",")
    serials_list = set(serials_list)
    global lb
    global dev_index
    # Checks to see if device is alive
    for serial in serials_list:
        if serial != '':
            serial = serial.strip()
            my_device = Device(serial, dev_index)
            # Adds the device to the list
            devices.append(my_device)
            dev_dic[serial] = 0
            devices[dev_index].info += "Added Device: " + my_device.serial + "\n"
            print "Added Device: " + serial
            logging.info('Previously connected device added: %s', serial)
            lb.insert(tk.END, serial)
            lb.itemconfig(dev_index, bg='green', fg='white', selectbackground="blue", selectforeground="white")
            dev_index += 1


def getlist(event):
    """
    Gets the current selected device
    :param event: Click on the evice to start event
    :return: Calls update screen with selected device
    """
    global lb
    index = int(lb.curselection()[0])
    global current_device
    current_device = index
    updatescreen(devices[index].info)


def runcommand(command, serial):
    """
    Sends the command to the server
    :param command: The command that goes to the server
    :param serial: The serial that should run the command
    """
    global server
    requests.post("http://" + server + ":80/gui_cmd_sent", data={'output': command, 'serial': serial})
    devices[current_device].info += "\n\nYour command: " + command + "\n"
    devices[current_device].info += "----------------------------" * 2
    updatescreen(devices[current_device].info)


def waitoutput():
    """
    Gets the output from the server that the client returns
    :return: The output obtained
    """
    global server
    global output_ready
    for i in xrange(sys.maxint):
        conn = httplib.HTTPConnection(server.strip() + ":80")
        conn.request("GET", "/gui_output_wait")
        r1 = conn.getresponse()
        check = r1.read()
        if check == "1":
            output_ready = "1"
        if output_ready == "1":
            print "\nReceived new output..."
            display_output()
            requests.post("http://" + server + ":80/received_output")
        time.sleep(.1)


def display_output():
    global output_ready
    conn = httplib.HTTPConnection(server.strip() + ":80")
    conn.request("GET", "/gui_get_output")
    r1 = conn.getresponse()
    output = r1.read()
    devices[current_device].info +=  output
    updatescreen(devices[current_device].info)
    output_ready = "0"
    conn.close()


def updatescreen(display):
    """
    Changes the screen on the gui to the desired display
    :param display: The info/data wanted the display on the gui
    """
    global textbox
    textbox.config(state=tk.NORMAL)
    textbox.delete('1.0', tk.END)
    textbox.insert(tk.END, display)
    textbox.see(tk.END)
    textbox.config(state=tk.DISABLED)


def changeinfo(command, entry_cmd):
    """
    Gets the command that the user inputted and sends it to the client
    Then, with the output received, it is displayed onto the screen of the gui
    :param command: The command received
    :param entry_cmd: The entrybox that the command was typed into
    :return: Updates the screen with the desired command and output
    """
    if devices[current_device].serial not in blacklist:
        logging.info('New command found: %s', command)
        entry_cmd.delete(0, tk.END)
        # displays the output from the run
        runcommand(command, devices[current_device].serial)
    else:
        updatescreen("Device is not connected!\nNot executing command.")


def createwindow(root):
    """
    Creates the gui window with all of its properties including,
    the menus, the scrollbar, the entrybox, and the display window
    :param root: The mainframe of the window
    """
    global lb
    global textbox
    # Menus
    dropDown = tk.Menu(root)
    root.config(menu=dropDown)
    actions = tk.Menu(dropDown)
    dropDown.add_cascade(label="Actions", menu=actions)
    actions.add_command(label='Device Info', command=deviceinfo)
    actions.add_command(label='Clear Devices', command=cleardevices)
    actions.add_command(label='Clear', command=clearall)
    actions.add_command(label='Clear log', command=clearlog)
    actions.add_command(label='Help', command=helpaction)
    actions.add_command(label='Geolocation', command=geolocation)
    # actions.add_command(label='Quit', command=root.destroy())
    lb = tk.Listbox(root, selectmode=tk.SINGLE)
    collecteddevices()
    lb.pack(side=tk.LEFT, fill=tk.Y)
    lb.bind('<ButtonRelease-1>', getlist)
    # Entrybox
    entry_cmd = tk.Entry(root, width=100)
    entry_cmd.pack(side=tk.BOTTOM)
    label_cmd = tk.Label(root, text="Command:")
    label_cmd.pack(side=tk.BOTTOM)
    entry_cmd.delete(0, tk.END)
    root.bind("<Return>", lambda x: changeinfo(entry_cmd.get(), entry_cmd))
    # Scrollbar
    scroll = tk.Scrollbar(root)
    textbox = tk.Text(root, height=40, width=125)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    textbox.pack(side=tk.TOP, fill=tk.Y)
    scroll.config(command=textbox.yview)
    textbox.config(yscrollcommand=scroll.set)


def postlogin():
    """
    Called after login is complete
    Creates all of the threads and widgets on the window
    This is the main window of the gui
    """
    root = tk.Tk()
    root.wm_title("AutoLogin_v1.0")
    frame = tk.Frame(root)
    frame.pack()
    createwindow(root)
    updatescreen(info)
    createscanner()
    root.mainloop()


def postloginthread():
    """
    Creates a new thread for the main gui
    """
    t3 = Thread(target=postlogin)
    t3.start()
    t4 = Thread(target=waitoutput)
    t4.start()


def suspenddevice(serial):
    """
    Disconnets the device from the list of devices
    :param serial: The devices needing to be disconnected
    :return:
    """
    global lb
    for dev in devices:
        if dev.serial == serial:
            lb.itemconfig(dev.index, bg='red', fg='white')
            blacklist.add(dev.serial)


def livingdevices():
    """
    Gets the living devices from the server and adds the new devices to the list
    If a device does not respond for 3 seconds then it will be labeled as disconnected
    """
    global server
    while True:
        conn = httplib.HTTPConnection(server + ":80")
        conn.request("GET", "/gui_get_life")
        r1 = conn.getresponse()
        life_string = r1.read()
        life_string = life_string[:-1]
        serial_val = life_string.split(",")
        active_serials = set()
        for combo in serial_val:
            data = combo.split("~")
            if data[0] != "":
                active_serials.add(data[0])
        for device in devices:
            if device.serial not in active_serials:
                suspenddevice(device.serial)
        time.sleep(2.5)
    conn.close()


def createscanner():
    """
    Creates the threads for checking for new devices and living devices
    """
    t = Thread(target=checknewdevice)
    t.start()
    t2 = Thread(target=livingdevices)
    t2.start()


def readdevice():
    """
    When a new device is found this function is called to add the device to
    the list of current connected devices
    """
    global server
    global lb
    conn = httplib.HTTPConnection(server.strip() + ":80")
    conn.request("GET", "/gui_get_device")
    r1 = conn.getresponse()
    serial = r1.read()
    global devices
    for device in devices:
        if device.serial == serial:
            if device.serial in blacklist:
                lb.itemconfig(device.index, bg='green', fg='white', selectbackground="blue", selectforeground="white")
                blacklist.remove(device.serial)
                return
            else:
                return
    global dev_index
    my_device = Device(serial, dev_index)
    devices.append(my_device)
    dev_dic[serial] = 0
    devices[dev_index].info += "Added Device: " + serial + "\n"
    print "Added Device: " + serial
    logging.info('New Device Added: \n%s', serial)
    logging.info('New Device index: \n%s', dev_index)
    dev_index += 1
    lb.insert(tk.END, serial)
    lb.itemconfig(dev_index - 1, bg='green')
    conn.close()


def checknewdevice():
    """
    Constantly checks for new devices
    Adds the new devices once they are connected to the server
    """
    global server
    global animation
    for i in xrange(sys.maxint):
        conn = httplib.HTTPConnection(server.strip() + ":80")
        conn.request("GET", "/gui_wait")
        sys.stdout.write("\r" + animation[i % len(animation)])
        sys.stdout.flush()
        r1 = conn.getresponse()
        new_device = r1.read()
        if new_device == "1":
            print "\nNew Device found..."
            readdevice()
        time.sleep(3)
    conn.close()


def checkcreds(root, url, user, password, ip):
    """
    Checks the credentials to ensure a valid login
    :param root: Mainframe where the window is held
    :param url: The url to be checed
    :param user: The user to be checked
    :param password: The password to be checked
    :param ip: The ip to be checked
    :param newattempts: The number of attempt made to login
    """
    global server
    global attempts
    server = "ec2-" + ip + ".compute-1.amazonaws.com"
    requests.post("http://" + server + ":80/gui_login_check", data={'URL': url, 'user': user, 'pass': password})
    conn = httplib.HTTPConnection(server + ":80")
    conn.request("GET", "/gui_login_check")
    r1 = conn.getresponse()
    check_cred = r1.read()
    print check_cred
    attempts += 1
    if check_cred == "1":
        print "Logged in by: " + user
        logging.info('User %s logged in...', user)
        root.destroy()
        postloginthread()
    elif attempts > 2:
        logging.info("Login failed after 3 attempts")
        quit()
    conn.close()

def main():
    """
    Begins the program and starts up the login window
    Calls the necessary functions to create the window and
    Binds controls and buttons in order to et to the next window
    """
    login_root = tk.Tk()
    login_root.wm_title("Login to Server")
    url = tk.Label(login_root, text="URL: ")
    username = tk.Label(login_root, text="Username: ")
    password = tk.Label(login_root, text="Password: ")
    ip = tk.Label(login_root, text="IP (XX-XX-XXX-XXX): ")
    entry_url = tk.Entry(login_root, width=30)
    entry_ip = tk.Entry(login_root, width=30)
    entry_user = tk.Entry(login_root, width=30)
    entry_pass = tk.Entry(login_root, show="*", width=30)
    url.grid(row=0, sticky=tk.E)
    ip.grid(row=1, sticky=tk.E)
    username.grid(row=2, sticky=tk.E)
    password.grid(row=3, sticky=tk.E)
    entry_url.grid(row=0, column=1, sticky=tk.E)
    entry_ip.grid(row=1, column=1, sticky=tk.E)
    entry_user.grid(row=2, column=1, sticky=tk.E)
    entry_pass.grid(row=3, column=1, sticky=tk.E)
    global attempts
    login_root.bind("<Return>", lambda x: checkcreds(login_root, entry_url.get(), entry_user.get(), entry_pass.get(),
                                                     entry_ip.get()))
    submit = tk.Button(login_root, text="Login",
                       command=lambda: checkcreds(login_root, entry_url.get(), entry_user.get(), entry_pass.get(),
                                                  entry_ip.get()))
    submit.grid(row=4, columnspan=2)
    login_root.mainloop()


if __name__ == "__main__":
    main()
