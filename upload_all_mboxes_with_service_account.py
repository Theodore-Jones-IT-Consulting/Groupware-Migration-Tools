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

# script is a work in progress and may have bugs

import os
import subprocess
import time

def create_tmux_session(session_name, command):
    """
    Creates a tmux session and runs the specified command in it.
    """
    try:
        # Create a new detached tmux session
        subprocess.check_call(['tmux', 'new-session', '-d', '-s', session_name])
        # Allow some time for tmux to set up the new session
        time.sleep(1)
        # Send the command to the tmux session, followed by 'Enter' to execute it
        subprocess.check_call(['tmux', 'send-keys', '-t', session_name, command, 'C-m'])
        print(f"Session {session_name} created and command sent.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating session {session_name}: {e}")

def process_user_folders(base_folder, dest_domain):
    """
    Processes each user folder, creating a tmux session for each and running the GYB command.
    """
    for folder in os.listdir(base_folder):
        folder_path = os.path.join(base_folder, folder)
        if os.path.isdir(folder_path) and 'mbox' in os.listdir(folder_path):
            email_prefix = folder.split('@')[0]
            session_name = f"gyb_{email_prefix}"
            dest_email = f"{email_prefix}@{dest_domain}"
            command = f"gyb --action restore-mbox --email {dest_email} --service-account --local-folder '{folder_path}/mbox'"
            create_tmux_session(session_name, command)
        else:
            print(f"Skipping {folder_path}, does not contain 'mbox' directory.")

if __name__ == "__main__":
    base_folder = input("Enter the path to the folder containing the email archives: ")
    if not os.path.isdir(base_folder):
        print("Error: The specified path does not exist or is not a directory.")
        exit(1)

    dest_domain = input("Enter the destination domain name: ")
    process_user_folders(base_folder, dest_domain)
