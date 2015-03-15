#!/usr/bin/env python

import smtplib
import os
import subprocess
import time
import datetime
from configuration import settings, sites


class UptimeLogger(object):
    """
    Creates a file to check the last status of the hostname. Works by creating a file when the site is down
    and removing it when it is up
    """
    def __init__(self, hostname):
        # Set the file name
        self.file_location = os.path.join(os.getcwd(), 'down_sites_list.txt')
        self.hostname = hostname
        # Create the down site file if it does not exist
        if not os.path.isfile(self.file_location):
            open(self.file_location, 'w+').close()

    def was_up(self):
        """
        Checks if the site was up last time. Returns a boolean
        """
        site_list = open(self.file_location, 'r')
        down_sites = site_list.readlines()
        site_list.close()
        # Check if the site was down
        for site in down_sites:
            if site.strip() == self.hostname:
                # The hostname was found in the file, which means it was down previously
                return False
        # The hostname was not found in the file
        return True

    def mark_down(self):
        """
        Mark the site as down
        """
        # Check if the file already exists in the list
        if not self.was_up():
            return
        site_list = open(self.file_location, 'a')
        site_list.write(self.hostname + "\n")
        site_list.close()

    def mark_up(self):
        """
        Mark the site as up
        """
        # Check if the site was not in the list initially
        if self.was_up():
            return
        site_list = open(self.file_location, 'r')
        down_sites = site_list.readlines()
        site_list.close()

        new_sites_list = []
        for site in down_sites:
            # Check for the site and remove it if found
            if site.strip() == self.hostname:
                continue
            new_sites_list.append(site)
        # Write the new list
        site_list = open(self.file_location, 'w')
        site_list.writelines(new_sites_list)
        site_list.close()


class UptimeChecker(object):
    """
    Checks the uptime of a site
    """

    def __init__(self, hostname):
        self.hostname = hostname
        self.check_up()

    def check_up(self):
        """
        Checks if the site is up and sets the class variables did_change and is_up
        """
        process = subprocess.Popen(
            'ping -c 1 ' + self.hostname,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        process.wait()
        uptime_logger = UptimeLogger(self.hostname)

        self.did_change = False
        if process.returncode == 0:
            # If the site is up, check if the site was previously down
            self.is_up = True

            if uptime_logger.was_up():
                # The site is still up
                print("\033[1;34mSite %s is still up\033[0m" % self.hostname)
            else:
                # The site went from down to up
                print ("\033[1;42mSite %s went back up\033[0m" % self.hostname)
                self.did_change = True
                uptime_logger.mark_up()
        else:
            # If the site was not previously down, send the email
            self.is_up = False
            if uptime_logger.was_up():
                # Site went down
                print ("\033[1;41mSite %s went down\033[0m" % self.hostname)
                self.did_change = True
                uptime_logger.mark_down()
            else:
                # Site is still down
                print ("\033[1;33mSite %s is still down\033[0m" % self.hostname)
        return self.is_up

ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

"""Sends an e-mail to the specified recipient."""
sender = settings["monitor_email"]
recipient = settings["recipient_email"]
subject = settings["email_subject"]
headers = ["From: " + sender,
           "Subject: " + subject,
           "To: " + recipient,
           "MIME-Version: 1.0",
           "Content-Type: text/html"]
headers = "\r\n".join(headers)
session = smtplib.SMTP(settings["monitor_server"], settings["monitor_server_port"])
session.ehlo()
session.starttls()
session.ehlo()
session.login(settings["monitor_email"], settings["monitor_password"])


for site in sites:
    checker = UptimeChecker(site)
    # The site status changed from it's last value, so send an email
    if checker.did_change:
        if checker.is_up:
            # The site went back up
            body = "%s went back up at %s" % (site, st)
            session.sendmail(sender, recipient, headers + "\r\n\r\n" + body)
        else:
            # The site went down
            body = "%s went down at %s" % (site, st)
            session.sendmail(sender, recipient, headers + "\r\n\r\n" + body)

session.quit()
