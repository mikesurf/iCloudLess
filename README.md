
# iCloudLess
In case you want to use *less* of your iCloud storage space ;)

This python app downloads the oldest files (photos and videos) from your iCloud account to your PC. And then optionally deletes those downloaded files in iCloud. You can configure how many files to keep in iCloud.

## Getting Started
- You'll need Python version 3 installed
- Git clone the repo to your computer

## Adjust settings in config.txt
- Set username and password variables to your icloud username and password
- Set target_dir to be the location where you want downloaded files to be stored on your computer (requires a trailing slash)
- Set num_files_to_keep_in_icloud to whatever number of photos you want to keep in your account after the app runs. The app will download (and delete) anything older than that number.
- Set delete_downloaded_files to TRUE if you want the app to delete photos from iCloud after downloading them to your computer

## Multiple config.txt files
- You can have any number of config*.txt files representing different icloud accounts
- If do have multiple config files, the app will prompt you to choose which account to use

## Run the app
1) Open a terminal in the directory where the repo is located and run the command: ```python icloud.py```
2) If two-factor authentication is enabled on your iCloud account, the app will ask which device to authentication with and you need to tell it which to use (e.g. 1, 2, etc.) and press enter
3) You should receive a *text message* (or pop-up code) to your device. Enter that into the app.
4) If you correctly entered the code but receive a message about failure to verify device, re-run the app and try again, it should work on the second or third attempt
5) Once two-factor authentication passes the app will begin downloading files to your computer. This might take a few minutes to download depending on how many files you have and your connection speed.

## Logging
A log of the app's activity will be recorded in run.log

## Where photos and videos are stored

By default, files are stored into a directory named according to what date the app runs ("run_dir_format" in config.txt specifies the date format), like this:

- Photos --> target_dir/run_dir_format/photos_dir

If any of your photos or videos are tagged as "favorites" in iCloud (meaning have the heart symbol on them), they will be copied (duplicated) to the "favorites" folder

- Favorites --> target_dir/run_dir_format/favorites_dir

And you can adjust the "target_dir", "photos_dir" and "favorites_dir" variables to your liking in config.txt

## FAQs

## Notes
- You may experience throttling from iCloud if you download too many photos too often. I was able to download well over 1000 files during my initial testing. But after a lot of testing within that same day I noticed when running the app after a few hundred files the app would experience a time-out (and would quit).
- If you set delete_downloaded_files=FALSE in config.txt, already downloaded files will be skipped and will not be re-downloaded
- For each file downloaded AND before the cloud file is deleted, the app compares the downloaded file size to the corresponding reported file size in the cloud, and if they are different the program exits. At least this way we do NOT delete something in the cloud that isn't fully downloaded.