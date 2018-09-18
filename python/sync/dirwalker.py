import os
from stat import S_ISDIR

# -----------------------------------------------------------------------------
# Python 2's directory-tree walker (os.walk) is slow, especially on Windows,
# and we also want the result of stats it performs on files so we can grab
# the mtime and size of the files as we see them.
#
# \param    basepath            Directory to crawl
# \yield                        (path, mutable-dirs, (file, stat))
#
def directory_walker(basepath,
                     chdir=os.chdir, listdir=os.listdir, stat=os.stat):

    # We're going to use chdir to avoid a lot of extraneous path handling
    # and processing. So we'll need to remember where we started.
    origin = os.getcwd()

    # Exception wrapper to ensure we cd back to origin in all cases.
    try:
        # Build a work queue of paths to explore starting with the top folder
        paths = [os.path.abspath(basepath)]

        while paths:
            # Grab the next task from the queue.
            path = paths.pop()

            # Move to that folder so everything can be '.' relative.
            chdir(path)

            # Create a string with the path separator suffixed to reduce operations
            prepped_path = path + os.path.sep

            # Track files and directories we see here, and create aliases to their
            # append functions so we can avoid a bunch of dictionary lookups.
            files, dirs = [], []
            add_file, add_dir = files.append, dirs.append

            # ignore anything starting with a dot and then inspect the entry.
            for entry in (e for e in listdir('.') if not e.startswith('.')):

                # get a stat on the entry so we can tell if it is a directory or not,
                # and also provide the stat to the invoker.
                try:
                    entry_stat = stat(entry)
                except OSError:
                    pass

                if S_ISDIR(entry_stat.st_mode):
                    add_dir((entry, entry_stat))
                else:
                    add_file((entry, entry_stat))

            yield path, dirs, files

            # Like os.walk, we allow the invoker to modify the dirs list, e.g
            # dirs[:] = []
            # Put whatever is left in the directories list onto the work queue
            paths.extend(prepped_path + d[0] for d in sorted(dirs))

    finally:
        os.chdir(origin)


