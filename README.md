# NM

### Huh?
NM is a video downloader with a lot of features, most of which are filters for fine-tuning your search

### How to use
##### Python 3.9 or greater required
- NM is a cmdline tool, no GUI
- It consists of 2 main download modules: `pages.py` for pages scanning, `ids.py` ‒ for video ids traversal
- See `requirements.txt` for additional dependencies. Install with:
  - `python -m pip install -r requirements.txt`
- Invoke `python pages.py --help` or `python ids.py --help` to list possible arguments for each module (the differences are minimal)
- For bug reports, questions and feature requests use our [issue tracker](https://github.com/trickerer01/NM/issues)

#### Search & filters
- NM supports searching (`pages.py` module) using native website API
  - `-search <STRING>` - search using raw string, matching all words (see below). Concatenate using `-`:
- Search is performed using search string matching all words (see below)
- Initial search results / ids list can be then filtered further using `extra tags` (see help for additional info)

##### Search rules
- How raw string search really works: when trying to match word(s) in the search string server iterates over post info exactly once, this means a single piece of post info may only match one word in search string, for example searching for `girl-girl` will return only a fraction of the results returned when searching for just `girl`. Words in provided string may match title, tags or author (uploader). Matching is partial so word 'all' will match 'tall', 'calling' and everything else containing this symbol sequence
 
#### Tags
- There is no list of existing tags. Video tagging is completely on uploaders. So better utilize...
- Wildcards. In any `extra tag` you can use symbols `?` and `*` for `any symbol` and `any number of any symbols` repectively
- If even more advanced approach is required you can also use regular expressions. To prevent syntax conflicts following regex symbols must be escaped using `` ` ``: `()?*.,-+` as well as `(?:` sequence (`` `(?: ``). Example: ``*[1`-5]`+`(finger{1`,3}|girl`)s`?`.`*`` converts to regex ``^.*[1-5]+(?:finger{1,3}|girl)s?.*$``. Notes:
  - No need to specify group as non-capturing
  - Some characters don't need escaping, like `|` or `[` there
  - You can combine wildcards and regular expressions within the same extra tag. Note how first `*` is converted as wildcard symbol while the ending `` `.`* `` specified explicitly as regex converts to the same characters pair
  - `` ` `` character is used for escaping because it isn't contained in any tag, artist or category name
- What makes `extra tags` different from search string is `tags` or `-tags` are being used as filters instead of search params, search string is passed using its own search argument (see full help) and all unknown arguments are automatically considered `extra tags`

#### Additional info
1. `OR` / `AND` groups:
  - `OR` group is a parenthesized tilda (**\~**) -separated group of tags
    - **(\<tag1>\~\<tag2>\~...\~\<tagN>)**
    - video matching **any** of the tags in `OR` group is considered matching that group
  - `AND` group is a parenthesized comma (**,**) -separated group of tags. Only negative `AND` group is possible ‒ to filter out videos having this unwanted **tags combination**
    - **-(\<tag1>,\<tag2>,...,\<tagN>)**
    - video matching **all** tags in `AND` group is considered matching that group

2. `--download-scenario` explained in detail:
  - Syntax: `--download-scenario SCRIPT` / `-script SCRIPT`
  - Scenario (script) is used to separate videos matching different sets of tags into different folders in a single pass
  - *SCRIPT* is a semicolon-separated sequence of '*\<subfolder>*<NOTHING>**:** *\<args...>*' groups (subqueries)
  - *SCRIPT* always contains spaces hence has to be escaped by quotes:
    - python ids.py \<args>... -script ***"***<NOTHING>sub1: tags1; sub2: tags2 ...***"***
  - Typically each next subquery is better exclude all required tags from previous one and retain excluded tags, so you know exactly what file goes where. But excluding previous required tags is optional - first matching subquery is used and if some item didn't match previous sub there is no point checking those tags again. **Subquery order matters**. Also, `-tags` contained in every subquery can be safely moved outside of script
    - ... -script "s1: *a b (c\~d)* **-e**; s2: **-a -b -c -d -e** *f g (h\~i)*; s3: **-a -b -c -d -e -f -g -h -i** *k*" `<< full script`
    - ... -script "s1: *a b (c\~d)* **-e**; s2: *f g (h\~i)* **-e**; s3: *k* **-e**" `<< no redundant excludes`
    - ... -script "s1: *a b (c\~d)*; s2: *f g (h\~i)*; s3: *k*" **-e** `<< "-e" moved outside of script`
  - Besides tags each subquery can also have `-quality` set ‒ videos matching that subquery will be downloaded in this quality
  - Subquery can also have `--use-id-sequence` flag set (see below) and match video ids
  - Subquery can also have its own `-duration` filter - only videos having duration within `-duration` bounds will be downloaded to that subfolder
  - You can also set `--untagged-policy always` for **one** subquery

3. Downloading a set of video ids
  - Syntax: `--use-id-sequence` / `-seq`, `ids.py` module only (or download scenario subquery)
  - Id sequence is used to download set of ids instead of id range
  - The sequence itself is an `extra tag` in a form of `OR` group of ids:
    - `(id=<id1>~id=<id2>~...~id=<idN>)`
  - Id sequence is used **instead** of id range, you can't use both
    - `python ids.py <args>... -seq (id=1337~id=9999~id=1001)`

4. File naming
  - File names are generated based on video *title* and *tags*:
  - Base template: ***\<prefix>\_\<id>\_(\<score>)_\<title>\_(\<tags>).\<ext>***. It can be adjusted via `-naming` argument
  - Non-descriptive or way-too-long tags will be dropped
  - If resulting file full path is too long to fit into 240 symbols, first the tags will be gradually dropped; if not enough title will be shrunk to fit; general advice is to not download to folders way too deep down the folder tree

5. Using 'file' mode
  - Although not required as cmdline argument, there is a default mode app runs in which is a `cmd` mode
  - `File` mode becomes useful when your cmdline string becomes **really long**. For example: Windows string buffer for console input is about 32767 characters long but standard `cmd.exe` buffer can only fit about 8192 characters, powershell ‒ about 16384. File mode is avalible for both `pages.py` and `ids.py` modules, of course, and can be used with shorter cmdline string as well
  - `File` mode is activated by providing 'file' as first argument and has a single option which is `-path` to a text file containing actual cmdline arguments for used module's cmd mode:
    - `python pages.py file -path <FILEPATH>`
  - Target file has to be structured as follows:
    - all arguments and values must be separated: one argument *or* value per line
    - quotes you would normally use in console window to escape argument value must be removed
    - only current module arguments needed, no python executable or module name needed, `cmd` mode can be omitted
      ```
      -start
      1
      -end
      20
      -path
      H:/long/folder name/with spaces (no quotes)/
      --log-level
      trace
      -script
      s1: (script~is~a~single~value); s2: -no_quotes_here_either
      ```

6. Unfinished files policy
  - Unexpected fatal errors, Ctrl-C and other mishaps will cause download(s) to end abruptly
  - By default when app manages to exit gracefully all unfinished files get deleted, at the same time all existing files are automatically considered completed
  - To check and resume existing unfinished files use `--continue-mode` (or `-continue`) option. This may be slower for non-empty folders due to additional network requests but safer in case of complex queries
  - To keep unfinished files use `--keep-unfinished` (or `-unfinish`) option. It acts as `--continue-mode` helper so it's recommended to use either both or none at all

7. Interrupt & resume
  - When downloading at large sometimes resulting download queue is so big it's impossible to process within reasonable time period and the process will be inevitably interrupted
  - There is only one way to make a 'safe' interruption which is to tap 'q' while in active console window and then tap it again after a small time period. This will signal the scanner to skip the rest of its queue and after all remaining downloads get processed the app will exit normally
  - To be able to resume without running the whole search process again use `--store-continue-cmdfile` option. Once initial video queue is formed a special 'continue' file will be stored and periodically updated in base download destination folder
  - Continue file contains cmdline arguments required to resume download, all provided parameters / options / download scenario / extra tags are preserved
  - It is strongly recommended to also include `--continue-mode` and `--keep-unfinished` options when using continue file
  - If download actually finishes without interruption stored continue file is automatically deleted
  - Continue file has to be used with `ids.py` module, `file` mode (see `using 'file' mode` above)

#### Examples
1. Pages
  - All videos by a single tag:
    - `python pages.py -pages 9999 -search STRING`
  - Up to 36 recent videos matching 2 words in 1080p, save to a custom location:
    - `python pages.py -pages 2 -path PATH -quality 1080p -search STRING1+STRING2`
  - All videos from user's playlist:
    - `python pages.py -pages 9999 -path PATH -quality 1080p -playlist_name USER_NAME`
  - All videos uploaded by a user, if tagged with either of 2 desired tags, in best quality, sorted into subfolders by several desired (known) authors, putting remaining videos into a separate folder, setup for interrupt & continue:
    - `python pages.py -pages 9999 -path PATH --store-continue-cmdfile -quality 1080p -uploader USER_NAME (TAG1~TAG2) -script "name1: AUTHOR1; name2: AUTHOR2; name3: AUTHOR3; rest: * -utp always"`

2. Ids
  - All existing videos in range:
    - `python ids.py -start 75000 -count 100`
    - `python ids.py -start 75000 -end 75099`
  - You can use the majority of arguments from `pages` examples. The only argument that is unique to `ids.py` module is `--use-id-sequence` (`-seq`), see above where it's explained in detail
