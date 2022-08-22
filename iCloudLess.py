import sys
import click
from pyicloud import PyiCloudService
from pathlib import Path
from shutil import copyfile
import logging
import configparser
import os
import re
import glob
from datetime import date, datetime


class iCloudLess:
    
    # Setup the class
    def __init__(self):
        # Setup logging
        logging.basicConfig(filename='run.log', encoding='utf-8', level=logging.INFO)
    
        # Determine which config file to use
        config_file = self.determine_config()

        # Configure the app
        Config = configparser.ConfigParser()
        Config.read(config_file)
        self.api = PyiCloudService(
            Config.get("iCloud Credentials", "username"), 
            Config.get("iCloud Credentials", "password")
        )

        # Perform two factor authentication (if needed)
        self.two_factor_authentication()

        self.num_files_to_keep_in_icloud = Config.get("Config", "num_files_to_keep_in_icloud")
        self.delete_downloaded_files = Config.getboolean("Config", "delete_downloaded_files")
        self.run_dir_format = Config.get("Paths", "run_dir_format")
        target_dir = Config.get("Paths", "target_dir") + date.today().strftime(self.run_dir_format) + "/"
        self.photos_path = target_dir + Config.get("Paths", "photos_dir")
        self.favorites_path = target_dir + Config.get("Paths", "favorites_dir")

        # Create the directory for this run
        self.create_dir(target_dir)
        
        # Create the photos directory for this run
        self.create_dir(self.photos_path)
        
        # Create the favorites directory for this run
        self.create_dir(self.favorites_path)
    
    # Figure out which config file to use and return its file name
    def determine_config(self):
        config_files = glob.glob('config*.txt') # read in the config files
        Config = configparser.ConfigParser()
        config_index = 0

        if(len(config_files) > 1):

            print("which account should we use?:")
            
            for index, config_file in enumerate(config_files):    
                Config.read(config_file)
                print(f"({index+1}) " + Config.get("iCloud Credentials", "username"))

            account = int(click.prompt("Which account should we use?"))
            print("Will use account number", account)
            config_index = account-1

        elif(len(config_files) == 1):
            config_index = 0
            
        else:
            print("Could not find a config file, now exiting...")
            exit()

        Config.read(config_files[config_index])
        print("Using account: " + Config.get("iCloud Credentials", "username"))

        return config_files[config_index]

    # Create a directory
    def create_dir(self, path):
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except:
                logging.error("Could not create directory: %s", path)
                exit()
            else:
                logging.info("Created directory: %s", path)
        else:
            logging.info("Using existin directory: %s", path)


    # Perform two factor authentication if the iCloud account requires it 
    def two_factor_authentication(self):
        if self.api.requires_2fa:
            print("Two-factor authentication required. Your trusted devices are:")

            devices = self.api.trusted_devices
            for i, device in enumerate(devices):
                print(
                    "  %s: %s"
                    % (i, device.get("deviceName", "SMS to %s" % device.get("phoneNumber")))
                )

            device = click.prompt("Which device would you like to use?", default=0)
            device = devices[device]
            if not self.api.send_verification_code(device):
                print("Failed to send verification code")
                sys.exit(1)

            code = click.prompt("Please enter validation code")
            if not self.api.validate_verification_code(device, code):
                print("Failed to verify verification code")
                sys.exit(1)
    
    # Loop through all oldest files from cloud, save to local file system and optionally delete from cloud
    def run(self):
        
        logging.info("Program started at %s...", datetime.now().strftime("%m/%d/%Y %H:%M:%S")) # This is UTC time
        #logging.info("Account is %s", + self.Config.get("iCloud Credentials", "username"))
        
        index = 0
        photos = self.api.photos.all # could also use for example: albums['Favorites']

        photos.direction = "DESCENDING" # this sorts the files in descending order so we end up downloading the oldest files first
        total_photos = len(photos)

        num = int(self.num_files_to_keep_in_icloud)

        s = "There are %s total photos in iCloud. Will download %s of the oldest photos and leave %s photos in cloud." % (total_photos, (total_photos - num), num)

        print(s)
        logging.info(s)
        
        for photo in photos:
            if index == (total_photos - num):
                break

            photo.filename_unique = self.generate_unique_file_name(photo)

            logging.info("********** Starting to process file %s: %s (added to cloud on %s)************", index+1, photo.filename, photo.added_date)
            
            # Copy file from cloud to local host
            self.save_file_from_icloud_to_local_file_system(photo)
            
            # If a photo is favorited, copy to the favorites folder
            if self.file_is_favorite(photo):
                self.copy_file_to_favorites(photo)

            # Delete the iCloud file if desired, since we know we have correctly downloaded the file from iCloud
            if self.delete_downloaded_files == True:
                self.delete_file_in_cloud(photo)
            
            logging.info("********** Finished processing file %s ************", photo.filename)

            index+=1

        logging.info("Completed program, now exiting...")

    # Generate a unique file name and this helps in case iCloud gives duplicates in the .filename property
    def generate_unique_file_name(self, photo):
        index = photo.filename.rfind('.')
        return re.sub(r'[^A-Za-z0-9_]', '', photo.filename[:index]) + '-' + photo._asset_record['recordName'] + photo.filename[index:]

    # Download and save a file to the local file system
    def save_file_from_icloud_to_local_file_system(self, photo):

        photos_path = self.photos_path + photo.filename_unique

        # Write to local file system
        try:
            # If the file does not yet exist
            if not Path(photos_path).is_file():
                # Download the file to memory
                download = photo.download('original')
                with open(photos_path, 'wb') as opened_file:
                    opened_file.write(download.raw.read())
                logging.info("%s was successfully downloaded and written to file system at %s", photo.filename_unique, photos_path)
            
            # If the file with the same name already exists
            else:
                # If the file size is the same as cloud file size, do nothing
                if Path(photos_path).stat().st_size == photo.size:
                    logging.info("%s is already a file, skipping", photos_path)
                    pass
                # If the file size is different than cloud file size...
                elif Path(photos_path).stat().st_size != photo.size:
                    logging.info("%s is already a file, will treat as a duplicate...", photos_path)
                    photos_path = photos_path.replace(photo.filename_unique, 'duplicate-'+photo.filename_unique)
                    logging.info("Duplicate photo path is %s", photos_path)
                    # Download the file to memory
                    download = photo.download('original')
                    with open(photos_path, 'wb') as opened_file:
                        opened_file.write(download.raw.read())
        except:
            logging.error("Could not open file %s to write on local file system. Now quitting...", photos_path)
            exit()
        
        else: 
            # Test that a file was successfully downloaded to the local system
            if Path(photos_path).is_file():
                #logging.info("%s is a file", photos_path)
                pass
            else:
                logging.error("File %s was not successfully created. Now quitting...", photos_path)
                exit()
            
            # Test that the file on local file system is same size as on cloud
            if Path(photos_path).stat().st_size == photo.size:
                logging.info("%s has file size of %s and is = cloud file size of %s", photos_path, Path(photos_path).stat().st_size, photo.size)
                
                # # Delete the iCloud file if desired, since we know we have correctly downloaded the file from iCloud
                # if self.delete_downloaded_files == True:
                #     self.delete_file_in_cloud(photo)

            else:
                logging.error("%s has file size of %s and is != cloud file size of %s", photos_path, Path(photos_path).stat().st_size, photo.size)
                logging.error("Now quitting...")
                exit()

    # Return true if the file is considered a favorite
    def file_is_favorite(self, file):
        return file._asset_record['fields']['isFavorite']['value'] == 1
    
    # Copy an already downloaded file (from photos_path) to the favorites location on local file system
    def copy_file_to_favorites(self, photo):
        
        photos_path = self.photos_path + photo.filename_unique
        favorites_path = self.favorites_path + photo.filename_unique
        
        # Copy the favorite photo to local file system
        logging.info("%s is favorite...", photo.filename_unique)
        try:
            # Copy file from photos to favorites
            copyfile(photos_path, favorites_path)
            logging.info("%s was successfully copied from photos to favorites at %s", photo.filename_unique, favorites_path)
        except:
            logging.error("Could not copy %s to %s on local file system. Now quitting...", photos_path, favorites_path)
            exit()
        
        else:
            # test that the favoriate file was successfully copied
            if Path(favorites_path).is_file():
                #logging.info("%s is a file", favorites_path)
                pass
            else:
                logging.error("%s Favorite file was not successfully created. Now quitting...", favorites_path)
                exit()
            
            if Path(favorites_path).stat().st_size == photo.size:
                logging.info("%s favorite has file size of %s is = cloud file size of %s", favorites_path, Path(favorites_path).stat().st_size, photo.size)
            else:
                logging.error("%s favorite has file size of %s is != cloud file size of %s", favorites_path, Path(favorites_path).stat().st_size, photo.size)
                logging.error("Now quitting...")
                exit()

    # Delete file in iCloud
    def delete_file_in_cloud(self, photo):
        try:
            photo.delete()
        except:
            logging.error("Could not delete photo from iCloud, now quitting...")
            exit()
        else:
            logging.info("Deleted photo %s from cloud", photo.filename_unique)

 
def main():
    print("Starting program...")
    i = iCloudLess()
    i.run()
    print("Program completed. See run.log for details.")

# Start of the app
if __name__ == "__main__":
    main()