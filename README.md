# NM

### Huh?
NM is a video downloader with a lot of features, most of which are filters for fine tuning your search

### How to use
##### Python 3.7 or greater required
- NM is a cmdline tool, no GUI
- It consists of 2 main download modules: `pages.py` for pages scanning, `ids.py` - for video ids traverse
- Invoke `python pages.py --help` or `python ids.py --help` for possible arguments for each module (the differences are minimal)
- See `requirements.txt` for additional module dependencies
- For bug reports, questions and feature requests use our [issue tracker](https://github.com/trickerer01/NM/issues)

#### Search & filters
- NM supports search using native website functionality
- Search (pages only) is performed using search string (see help for more info), comparing every word against title or tags, partial match required: searching for 'all' will match titles containing 'tall', 'call' and so on
- Initial search results / ids list can be then filtered further using *extra tags* (see help for additional info)

#### Tags
- There is no list of existing tags. Tags videos have are completely on uploaders. So, better utilize...
- Wildcards. In any kind of tag you can use symbols `?` and `*` for 'any symbol' and 'any number of any symbols' repectively.
- Tags ~~containing wildcards~~ aren't validated, they can be anything

#### Additional info
1. `OR` / `AND` groups:
  - `OR` group is a parenthesized tilda (**\~**) -separated group of tags:
    - **(\<tag1>\~\<tag2>\~...\~\<tagN>)**
    - video containing **any** of the tags in `OR` group is considered matching that group
  - `AND` group is a parenthesized comma (**,**) -separated group of tags. It is only used as negative group, for exclusion:
    - **-(\<tag1>,\<tag2>,...,\<tagN>)**
    - video containing **all** tags in `AND` group is considered matching that group
    - negative `AND` group are for filtering out videos having this undesired **tags combination**

2. `--download-scenario` explained in detail:
   - Syntax: `--download-scenario SCRIPT` / `-script SCRIPT`
   - Scenario (script) is used to separate videos matching different sets of tags into different folders in a single pass
   - *SCRIPT* is a semicolon-separated sequence of '*\<subfolder>*<NOTHING>**:** *\<args...>*' groups (subqueries)
   - *SCRIPT* always contains spaces hence has to be escaped by quotes:
     - python ids.py \<args>... -script ***"***<NOTHING>sub1: tags1; sub2: tags2 ...***"***
   - Typically each next subquery is better exclude all required tags from previous one and retain excluded tags, so you know exactly what file goes where. But excluding previous required tags is optional - first matching subquery is used and if some item didn't match previous sub there is no point checking those tags again. **Subquery order matters**. Also, `-tags` contained in each subquery can be safely moved outside of script. Example:
     - ... -script "s1: a b (c\~d) **-e**; s2: **-a -b -c -d -e** f g (h\~i); s3: **-a -b -c -d -e -f -g -h -i** k" `<< full script`
     - ... -script "s1: a b (c\~d) **-e**; s2: **f g (h\~i) -e**; s3: **k -e**" `<< no redundant excludes`
     - ... **-e** -script "s1: **a b (c\~d)**; s2: **f g (h\~i)**; s3: **k**" `<< "-e" moved outside of script`
   - Besides tags, each subquery can also have `-quality` set, which will be used to download files matching that subquery. You can also set `-uvp always` for **one** subquery
   - Instead of pure tags subquery can also use `--use-id-sequence:` / `-seq` (see below) so instead of checking tags subquery will match ids. Such a subquery is better be first in script

3. `--use-id-sequence`:
  - Syntax: `--use-id-sequence SEQUENCE` / `-seq SEQUENCE`, ***ids.py*** only
  - Id sequence is used to download set of ids instead of id range
  - *SEQUENCE* is an `OR` group of ids:
    - **(id=\<id1>\~id=\<id2>\~...\~id=\<idN>)**
  - Id sequence is used **INSTEAD** of id range, you can't use both
    - python ids.py \<args>... -seq (id=1337\~id=9999\~id=1001)

4. File naming
  - File names are generated based on video *title* and *tags*:
  - Base template: ***nm\_\<video_id>\_\<score>\_\<title>\_(\<tags>).\<ext>***. It can adjusted it using `-naming` argument
  - Non-descriptive or way-too-long tags will be dropped
  - If resulting file full path is too long to fit into 240 symbols, first the tags will be gradually dropped; if not enough, title will be shrunk to fit; general advice: do not download to folders way too deep down the folder tree

5. Using 'file' mode
  - Although not required as cmdline argument, there is a default mode app runs in which is a `cmd` mode
  - `File` mode becomes useful when your cmdline string becomes **really long**. For example: Windows string buffer for console input is about 32767 characters long but standard `cmd.exe` buffer can only fit about 8192 characters, powershell - about 16384. File mode is avalible for both `pages` and `ids` modules, of course, and can be used with shorter cmdline string as well
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
  - By default, when app manages to exit gracefully, all unfinished files get deleted, and all existing files are automatically considered completed
  - To check and resume existing unfinished files use `--continue-mode` (or `-continue`). This may be slower for non-empty folders due to additional network requests but safer in case of complex queries
  - To keep unfinished files use `--keep-unfinished` (or `-unfinish`). It acts as `--continue-mode` helper so it's recommended to use either both or none at all
