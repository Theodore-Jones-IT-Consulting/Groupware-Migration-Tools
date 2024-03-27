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

import os
import re
import zipfile
import shutil
import sys
import mailbox
import logging

# Configure logging
logging.basicConfig(filename='unroll.log', level=logging.ERROR)

def extract_user_id(filename):
    match = re.search(r'^takeout-\d{8}T\d{6}Z', filename)
    if match:
        return match.group()
    return None

def extract_email(to_field):
    match = re.search(r'[\w\.-]+@[\w\.-]+', to_field)
    if match:
        return match.group()
    return None

def process_archives(folder_path):
    print(f"Processing archives in: {folder_path}")
    
    user_files = {}
    for file in os.listdir(folder_path):
        if file.endswith('.zip'):
            user_id = extract_user_id(file)
            if user_id:
                if user_id not in user_files:
                    user_files[user_id] = []
                user_files[user_id].append(file)
    
    print("Detected User IDs:")
    for user_id in user_files:
        print(user_id)
    print("---")
    
    for user_id, files in user_files.items():
        print(f"Processing files for user: {user_id}")
        user_folder = os.path.join(folder_path, user_id)
        os.makedirs(user_folder, exist_ok=True)
        
        # Extract all zip files for the user
        for file in files:
            zip_path = os.path.join(folder_path, file)
            print(f"Extracting archive: {file}")
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(user_folder)
            except Exception as e:
                logging.error(f"Error extracting archive {file}: {str(e)}")
            
            print(f"Copying archive to zips folder: {file}")
            zip_dest_folder = os.path.join(user_folder, 'zips')
            os.makedirs(zip_dest_folder, exist_ok=True)
            try:
                shutil.copy2(zip_path, zip_dest_folder)
            except Exception as e:
                logging.error(f"Error copying archive {file} to zips folder: {str(e)}")
        
        # Organize drive contents after all zip files are extracted
        organize_drive_contents(os.path.join(user_folder, 'Takeout'))
        
        # Parse archive_browser.html to get user email address
        archive_browser_path = os.path.join(user_folder, 'Takeout', 'archive_browser.html')
        email = None
        if os.path.exists(archive_browser_path):
            with open(archive_browser_path, 'r') as file:
                content = file.read()
                match = re.search(r'<h1 class="header_title">Archive for (.+?)</h1>', content)
                if match:
                    email = match.group(1)
                    new_user_folder = os.path.join(folder_path, email)
                    if not os.path.exists(new_user_folder):
                        try:
                            shutil.move(user_folder, new_user_folder)
                            user_folder = new_user_folder
                        except Exception as e:
                            logging.error(f"Error renaming user folder {user_folder} to {email}: {str(e)}")
        
        # Move Mbox files from Takeout/Mail to mbox folder
        mail_folder = os.path.join(user_folder, 'Takeout', 'Mail')
        if os.path.exists(mail_folder):
            for item in os.listdir(mail_folder):
                if item.endswith('.mbox'):
                    mbox_folder = os.path.join(user_folder, 'mbox')
                    os.makedirs(mbox_folder, exist_ok=True)
                    try:
                        shutil.move(os.path.join(mail_folder, item), mbox_folder)
                    except Exception as e:
                        logging.error(f"Error moving Mbox file {item} to mbox folder: {str(e)}")
        
        print(f"Finished processing files for user: {user_id}")
        print("---")
    
    print("Finished extracting all zip files.")
    print("---")
    
    # Process separate Mbox files
    for file in os.listdir(folder_path):
        if file.endswith('.mbox'):
            mbox_path = os.path.join(folder_path, file)
            mbox = mailbox.mbox(mbox_path)
            email_counts = {}
            num_messages = len(mbox)
            start_index = max(0, num_messages - 500)
            for i in range(start_index, num_messages):
                msg = mbox[i]
                to_field = msg['To']
                if to_field:
                    to_email = extract_email(to_field)
                    if to_email:
                        email_counts[to_email] = email_counts.get(to_email, 0) + 1
            if email_counts:
                most_common_email = max(email_counts, key=email_counts.get)
                user_folder = os.path.join(folder_path, most_common_email)
                if os.path.exists(user_folder):
                    mbox_dest_folder = os.path.join(user_folder, 'mbox')
                    os.makedirs(mbox_dest_folder, exist_ok=True)
                    try:
                        shutil.copy2(mbox_path, mbox_dest_folder)
                    except Exception as e:
                        logging.error(f"Error copying Mbox file {file} to {mbox_dest_folder}: {str(e)}")
    
    print("Finished processing separate Mbox files.")
    print("---")
    
    print("Processing completed.")
    
    # Check for users without Mbox files and users with multiple Mbox files
    users_without_mbox = []
    users_with_multiple_mbox = []
    for user_folder in os.listdir(folder_path):
        user_folder_path = os.path.join(folder_path, user_folder)
        if os.path.isdir(user_folder_path):
            mbox_folder = os.path.join(user_folder_path, 'mbox')
            if os.path.exists(mbox_folder):
                mbox_count = len([f for f in os.listdir(mbox_folder) if f.endswith('.mbox')])
                if mbox_count == 0:
                    users_without_mbox.append(user_folder)
                elif mbox_count > 1:
                    users_with_multiple_mbox.append(user_folder)
            else:
                users_without_mbox.append(user_folder)
    
    print("Users without Mbox files:")
    for user in users_without_mbox:
        print(user)
    
    print("Users with multiple Mbox files:")
    for user in users_with_multiple_mbox:
        print(user)

def organize_drive_contents(takeout_folder):
    drive_folder = None
    for folder_name in ['Drive', 'drive']:
        possible_folder_path = os.path.join(takeout_folder, folder_name)
        if os.path.isdir(possible_folder_path):
            drive_folder = possible_folder_path
            break
    
    if drive_folder:
        other_services_folder = os.path.join(takeout_folder, 'Other Google Services')
        os.makedirs(other_services_folder, exist_ok=True)
        
        # Move non-Drive items to Other Google Services
        for item in os.listdir(takeout_folder):
            item_path = os.path.join(takeout_folder, item)
            if item_path not in [drive_folder, other_services_folder] and os.path.isdir(item_path):
                target_path = os.path.join(other_services_folder, item)
                try:
                    shutil.move(item_path, target_path)
                    print(f"Moved {item} to Other Google Services")
                except Exception as e:
                    logging.error(f"Error moving {item} to Other Google Services: {str(e)}")
        
        # Move Drive contents to Takeout
        for item in os.listdir(drive_folder):
            try:
                shutil.move(os.path.join(drive_folder, item), takeout_folder)
                print(f"Moved {item} from Drive to Takeout")
            except Exception as e:
                logging.error(f"Error moving {item} from Drive to Takeout: {str(e)}")
        
        # Remove the Drive folder
        try:
            os.rmdir(drive_folder)
            print("Removed Drive folder")
        except OSError as e:
            logging.error(f"Error removing Drive folder: {str(e)}")
    else:
        print("Drive folder not found. Skipping organization of Drive contents.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python takeout_unroll.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory.")
        sys.exit(1)
    
    process_archives(folder_path)
