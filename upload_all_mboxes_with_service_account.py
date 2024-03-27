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
import re
import concurrent.futures

def run_gyb_command(user_folder):
    mbox_folder = os.path.join(user_folder, 'mbox')
    if os.path.exists(mbox_folder):
        email = os.path.basename(user_folder)
        email_without_at = email.replace('@', '')
        tmux_window_name = f"{email_without_at}_email"

        # Create a new tmux window for the user
        subprocess.run(['tmux', 'new-window', '-n', tmux_window_name, '-d'])

        # Run the gyb command in the tmux window
        gyb_command = [
            'tmux', 'send-keys', '-t', tmux_window_name,
            f"gyb --action restore-mbox --email {email} --service-account --local-folder {mbox_folder}",
            'Enter'
        ]
        subprocess.run(gyb_command)

def process_users(folder_path):
    user_folders = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]

    # Configure tmux to keep the output visible even after the process completes
    subprocess.run(['tmux', 'set-option', '-g', 'remain-on-exit', 'on'])

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_gyb_command, user_folder) for user_folder in user_folders]
        concurrent.futures.wait(futures)

    print("Finished uploading Mbox files for all users.")

if __name__ == '__main__':
    folder_path = input("Enter the path to the folder containing the unrolled takeout archive: ")
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory.")
        exit(1)

    process_users(folder_path)
