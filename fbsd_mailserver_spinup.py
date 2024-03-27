'''
This software is Copyright (c) 2024 Theodore Jones Information Technology Consulting 
(a DBA of Blueprint Cyber Solutions LLC)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to elsewhere, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

# script is a work in progress and may have bugs or might not work at all.

import os
import subprocess

def setup_email_server():
    # Install necessary packages
    subprocess.run(["pkg", "install", "postfix", "dovecot", "dovecot-pigeonhole", "spamassassin", "opendkim"])

    # Prompt user for configuration settings
    relay_host = input("Enter the relay host (e.g., smtp-relay.example.com): ")
    relay_port = input("Enter the relay port (e.g., 587): ")
    relay_username = input("Enter the relay username: ")
    relay_password = input("Enter the relay password: ")
    server_hostname = input("Enter the server hostname: ")

    # Generate SSL certificates
    os.makedirs("/usr/local/etc/mail/ssl", exist_ok=True)
    subprocess.run(["openssl", "req", "-newkey", "rsa:4096", "-nodes", "-keyout", "/usr/local/etc/mail/ssl/key.pem",
                    "-x509", "-days", "365", "-out", "/usr/local/etc/mail/ssl/cert.pem"])
    subprocess.run(["chown", "-R", "postfix:postfix", "/usr/local/etc/mail/ssl"])
    subprocess.run(["chmod", "600", "/usr/local/etc/mail/ssl/*"])

    # Configure Postfix
    postfix_config = f"""
mydestination = localhost.${{mydomain}}, localhost
mynetworks_style = host
myorigin = ${{mydomain}}
relayhost = [{relay_host}]:{relay_port}
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/usr/local/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
smtp_tls_security_level = may
smtp_tls_CAfile = /etc/ssl/cert.pem
virtual_alias_domains = 
virtual_alias_maps = hash:/usr/local/etc/postfix/virtual
milter_default_action = accept
milter_protocol = 2
smtpd_milters = unix:/var/run/opendkim/opendkim.sock
non_smtpd_milters = unix:/var/run/opendkim/opendkim.sock
smtpd_tls_cert_file = /usr/local/etc/mail/ssl/cert.pem
smtpd_tls_key_file = /usr/local/etc/mail/ssl/key.pem
smtpd_tls_security_level = may
smtpd_tls_auth_only = yes
"""
    with open("/usr/local/etc/postfix/main.cf", "w") as f:
        f.write(postfix_config)

    # Configure Postfix relay credentials
    with open("/usr/local/etc/postfix/sasl_passwd", "w") as f:
        f.write(f"[{relay_host}]:{relay_port} {relay_username}:{relay_password}\n")
    subprocess.run(["postmap", "/usr/local/etc/postfix/sasl_passwd"])

    # Configure Dovecot
    dovecot_config = """
protocols = imap
ssl = required
ssl_cert = </usr/local/etc/mail/ssl/cert.pem
ssl_key = </usr/local/etc/mail/ssl/key.pem
auth_username_format = %n
"""
    with open("/usr/local/etc/dovecot/dovecot.conf", "w") as f:
        f.write(dovecot_config)

    dovecot_auth_config = """
disable_plaintext_auth = yes
auth_mechanisms = plain login
passdb {
  driver = passwd-file
  args = /usr/local/etc/dovecot/passwd
}
userdb {
  driver = static
  args = uid=mail gid=mail home=/var/mail/%d/%n
}
"""
    with open("/usr/local/etc/dovecot/conf.d/10-auth.conf", "w") as f:
        f.write(dovecot_auth_config)

    dovecot_mail_config = """
mail_location = maildir:~/Maildir
"""
    with open("/usr/local/etc/dovecot/conf.d/10-mail.conf", "w") as f:
        f.write(dovecot_mail_config)

    # Configure SpamAssassin
    spamassassin_config = """
rewrite_header Subject *****SPAM*****
report_safe 0
"""
    with open("/usr/local/etc/mail/spamassassin/local.cf", "w") as f:
        f.write(spamassassin_config)

    # Integrate SpamAssassin with Postfix
    postfix_master_config = """
spamassassin unix -     n       n       -       -       pipe
  user=nobody argv=/usr/local/bin/spamc -f -e /usr/sbin/sendmail -oi -f ${sender} ${recipient}
"""
    with open("/usr/local/etc/postfix/master.cf", "a") as f:
        f.write(postfix_master_config)

    with open("/usr/local/etc/postfix/main.cf", "a") as f:
        f.write("content_filter = spamassassin\n")

    # Configure OpenDKIM
    os.makedirs("/usr/local/etc/mail/dkim", exist_ok=True)

    opendkim_config = f"""
Canonicalization relaxed/simple
ExternalIgnoreList refile:/usr/local/etc/mail/opendkim/TrustedHosts
InternalHosts refile:/usr/local/etc/mail/opendkim/TrustedHosts
KeyTable refile:/usr/local/etc/mail/opendkim/KeyTable
SigningTable refile:/usr/local/etc/mail/opendkim/SigningTable
Mode sv
PidFile /var/run/opendkim/opendkim.pid
UMask 002
UserID postfix:postfix
"""
    with open("/usr/local/etc/mail/opendkim.conf", "w") as f:
        f.write(opendkim_config)

    trusted_hosts = f"""
127.0.0.1
::1
localhost
{server_hostname}
"""
    with open("/usr/local/etc/mail/opendkim/TrustedHosts", "w") as f:
        f.write(trusted_hosts)

    # Start services
    subprocess.run(["service", "postfix", "start"])
    subprocess.run(["service", "dovecot", "start"])
    subprocess.run(["service", "sa-spamd", "start"])
    subprocess.run(["service", "opendkim", "start"])

    print("Email server setup completed.")

def add_domain():
    domain = input("Enter the domain name: ")

    # Add the domain to the Postfix configuration
    with open("/usr/local/etc/postfix/main.cf", "a") as f:
        f.write(f"virtual_alias_domains = {domain}\n")

    # Generate DKIM keys for the domain
    subprocess.run(["opendkim-genkey", "-D", "/usr/local/etc/mail/dkim", "-d", domain, "-s", "default"])

    # Add DKIM configuration for the domain
    with open("/usr/local/etc/mail/opendkim/KeyTable", "a") as f:
        f.write(f"default._domainkey.{domain} {domain}:default:/usr/local/etc/mail/dkim/default.private\n")
    with open("/usr/local/etc/mail/opendkim/SigningTable", "a") as f:
        f.write(f"*@{domain} default._domainkey.{domain}\n")

    print(f"Domain {domain} added successfully.")

def add_user():
    email = input("Enter the email address: ")
    password = input("Enter the password: ")

    # Add the user to the Dovecot password file
    with open("/usr/local/etc/dovecot/passwd", "a") as f:
        f.write(f"{email}:{{PLAIN}}{password}\n")

    # Create the user's mailbox directory
    domain = email.split("@")[1]
    user = email.split("@")[0]
    os.makedirs(f"/var/mail/{domain}/{user}", exist_ok=True)

    print(f"User {email} added successfully.")

def map_email():
    email = input("Enter the email address: ")
    user = input("Enter the username: ")

    # Add the email-to-user mapping to the Postfix virtual alias map
    with open("/usr/local/etc/postfix/virtual", "a") as f:
        f.write(f"{email} {user}\n")

    # Regenerate the virtual alias map
    subprocess.run(["postmap", "/usr/local/etc/postfix/virtual"])

    print(f"Email {email} mapped to user {user} successfully.")

def main_menu():
    while True:
        print("\nEmail Server Management")
        print("1. Setup Email Server")
        print("2. Add Domain")
        print("3. Add User")
        print("4. Map Email to User")
        print("5. Exit")

        choice = input("Enter your choice (1-5): ")

        if choice == "1":
            setup_email_server()
        elif choice == "2":
            add_domain()
        elif choice == "3":
            add_user()
        elif choice == "4":
            map_email()
        elif choice == "5":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()
