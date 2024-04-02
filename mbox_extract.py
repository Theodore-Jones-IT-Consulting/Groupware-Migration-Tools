import mailbox
import re

# Configure your search pattern and file paths here
pattern = re.compile(r'hello@aspirelosangeles.com', re.IGNORECASE)
input_mbox_path = '/root/letty.mbox'  # Update this to your mbox file path
output_mbox_path = '/root/output.mbox'  # The path where you want to save matching emails

def extract_emails(input_path, output_path, search_pattern):
    # Open the existing mbox file
    print("Opening the Mbox")
    mbox = mailbox.mbox(input_path)
    print("Opened the Mbox")
    # Create a new mbox file for the output
    output_mbox = mailbox.mbox(output_path)
    print("Created the Output")
    # Iterate through messages in the mbox
    print("Starting to Iterate Through the Messages")
    first_msg = 0
    for message in mbox:
        if first_msg == 0:
           print("First Message") 
           first_msg = 1
	try:
           # Convert message to string and search for the pattern
           if search_pattern.search(message.as_string()):
            # If the pattern is found, add the message to the output mbox
            output_mbox.add(message)

    # Close and flush the output mbox to save it
    output_mbox.flush()
    output_mbox.close()

# Run the function with the configured parameters
extract_emails(input_mbox_path, output_mbox_path, pattern)
