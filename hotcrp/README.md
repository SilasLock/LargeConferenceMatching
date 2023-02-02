# hotcrp
This is code for producing the files in the `data` directory, which is used as input for the matching program.

# Instructions
First, three empty folders must be created, named after the DATA_WITH_NONREVIEWERS, DATA_WITH_EMAILS_FOLDER, and DATA_FOLDER fields in the `config.py` file.

Second, you'll need to acquire the files

```
    HOTCRP_PCINFO_CSV,
    HOTCRP_DATA_JSON,
    HOTCRP_ALLPREFS_CSV,
    REVIEWER_EXPERIENCE_CSV,
    SS_SCORES_CSV,
    SS_CONFLICTS_CSV,
    ACL_SCORES_CSV,
    COAUTHOR_DISTANCE_FILE_NAME
```
and place them in the current directory. These can be acquired via the hotcrp portal and, for `COAUTHOR_DISTANCE_FILE_NAME`, the shared Google drive folder.

With all the data in position, you can then run the following three commands:
```
    python hotcrp_to_lcm.py
    python remove_nonreviewer_emails.py
    python replace_emails_with_numbers.py
```
The final output should be located in the `data` directory.
