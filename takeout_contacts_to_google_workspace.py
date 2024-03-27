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
import sys
import time
import re
import vobject
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_or_create_contact_group(service, group_name, group_cache):
    if group_name in group_cache:
        return group_cache[group_name]

    results = service.contactGroups().list().execute()
    for group in results.get('contactGroups', []):
        if group['name'] == group_name:
            group_cache[group_name] = group['resourceName']
            return group['resourceName']

    # If the group doesn't exist, create it
    new_group = {'contactGroup': {'name': group_name}}
    created_group = service.contactGroups().create(body=new_group).execute()
    group_cache[group_name] = created_group['resourceName']
    return created_group['resourceName']

def main(json_path, user_email, contacts_folder, batch_delay=5):
    creds = service_account.Credentials.from_service_account_file(json_path, scopes=['https://www.googleapis.com/auth/contacts'])
    delegated_creds = creds.with_subject(user_email)
    service = build('people', 'v1', credentials=delegated_creds)

    imported_contacts = set()
    group_cache = {}
    max_retries = 3  # Maximum number of retries for API requests

    contacts_to_create = []
    read_mask = 'names,emailAddresses,phoneNumbers,organizations,addresses,biographies,memberships,birthdays,urls,userDefined'
    sources = ['READ_SOURCE_TYPE_CONTACT']

    for root, dirs, files in os.walk(contacts_folder):
        for file in files:
            if file.endswith('.vcf'):
                with open(os.path.join(root, file), 'r') as f:
                    vcf_data = f.read()
                    contacts = vobject.readComponents(vcf_data)

                    for contact in contacts:
                        try:
                            name = contact.fn.value if hasattr(contact, 'fn') else ''
                            email = [{'value': e.value} for e in contact.contents['email']] if 'email' in contact.contents else []

                            if (name, tuple(e['value'] for e in email)) in imported_contacts:
                                continue

                            imported_contacts.add((name, tuple(e['value'] for e in email)))

                            given_name = contact.n.value.given if hasattr(contact, 'n') else ''
                            family_name = contact.n.value.family if hasattr(contact, 'n') else ''
                            phone = [{'value': p.value} for p in contact.contents['tel']] if 'tel' in contact.contents else []
                            organization = contact.org.value[0] if hasattr(contact, 'org') else ''
                            title = contact.title.value if hasattr(contact, 'title') else ''
                            note = contact.note.value if hasattr(contact, 'note') else ''
                            birthday = contact.bday.value if hasattr(contact, 'bday') else ''
                            url = [{'value': u.value} for u in contact.contents['url']] if 'url' in contact.contents else []

                            address = {}
                            if hasattr(contact, 'adr'):
                                address['streetAddress'] = contact.adr.value.street
                                address['city'] = contact.adr.value.city
                                address['region'] = contact.adr.value.region
                                address['postalCode'] = contact.adr.value.code
                                address['country'] = contact.adr.value.country

                            memberships = []
                            if hasattr(contact, 'categories'):
                                for category in contact.categories.value:
                                    group_resource_name = get_or_create_contact_group(service, category, group_cache)
                                    memberships.append({'contactGroupMembership': {'contactGroupResourceName': group_resource_name}})

                            user_defined = []
                            if note:
                                custom_field_pattern = re.compile(r'\\n(.*?): (.*)')
                                custom_fields = custom_field_pattern.findall(note)
                                for field in custom_fields:
                                    key = field[0].strip()
                                    value = field[1].strip()
                                    user_defined.append({'key': key, 'value': value})

                            birthday_parts = [birthday[0:4], birthday[4:6], birthday[6:8]]
                            formatted_birthday = '-'.join(filter(None, birthday_parts))

                            contact_to_create = {
                                'names': [{'givenName': given_name, 'familyName': family_name}],
                                'emailAddresses': email,
                                'phoneNumbers': phone,
                                'organizations': [{
                                    'name': organization,
                                    'title': title
                                }],
                                'addresses': [address] if address else [],
                                'biographies': [{'value': note}] if note else [],
                                'birthdays': [{'date': {'year': int(birthday_parts[0]), 'month': int(birthday_parts[1]), 'day': int(birthday_parts[2])}}] if birthday else [],
                                'urls': url,
                                'userDefined': user_defined,
                                'memberships': memberships
                            }

                            contacts_to_create.append({'contactPerson': contact_to_create})

                            if len(contacts_to_create) == 200:
                                retries = 0
                                while retries < max_retries:
                                    try:
                                        batch_response = service.people().batchCreateContacts(
                                            body={
                                                'contacts': contacts_to_create,
                                                'readMask': read_mask,
                                                'sources': sources
                                            }
                                        ).execute()
                                        print(f"Batch created {len(contacts_to_create)} contacts")
                                        contacts_to_create = []
                                        break
                                    except Exception as e:
                                        print(f"Error creating batch of contacts")
                                        print(str(e))
                                        retries += 1
                                        if retries < max_retries:
                                            print(f"Retrying in {batch_delay} seconds...")
                                            time.sleep(batch_delay)
                                        else:
                                            print("Max retries reached. Skipping batch.")

                                # Delay between batches
                                time.sleep(batch_delay)

                        except Exception as e:
                            print(f"Error processing contact: {contact}")
                            print(str(e))

    # Create any remaining contacts
    if contacts_to_create:
        retries = 0
        while retries < max_retries:
            try:
                batch_response = service.people().batchCreateContacts(
                    body={
                        'contacts': contacts_to_create,
                        'readMask': read_mask,
                        'sources': sources
                    }
                ).execute()
                print(f"Batch created {len(contacts_to_create)} contacts")
                contacts_to_create = []
                break
            except Exception as e:
                print(f"Error creating batch of contacts")
                print(str(e))
                retries += 1
                if retries < max_retries:
                    print(f"Retrying in {batch_delay} seconds...")
                    time.sleep(batch_delay)
                else:
                    print("Max retries reached. Skipping batch.")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python takeout_contacts_to_google_workspace.py <path_to_json> <user_email> <path_to_contacts_folder>")
        sys.exit(1)

    json_path = sys.argv[1]
    user_email = sys.argv[2]
    contacts_folder = sys.argv[3]

    main(json_path, user_email, contacts_folder)
