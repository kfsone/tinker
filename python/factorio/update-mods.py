#! /usr/bin/env python

import argparse
from   distutils.version import LooseVersion
import glob
import json
import logging
import os
import re
import requests
import resource
import sys

# Try "tqdm" for progress bar reporting
try:
    import tqdm
except:
    tqdm = None


class ProgressBar(object):
    if tqdm:
        def __init__(self, filename, num_bytes):
            self.pb = tqdm.tqdm(desc=filename, total=num_bytes, unit_scale=True, unit='B', leave=True)

        def update(self, progress):
            self.pb.update(progress)

        def end(self):
            self.pb.close()

    else:
        def __init__(self, filename, num_bytes):
            self.num_bytes = num_bytes

        def update(self, progress):
            pctg = progress * 100.0 / self.num_bytes
            bar  = '|' * min(int(pctg / 10), 10)
            kb   = progress / 1024.0
            sys.stdout.write("%5.1f%% [%10s] %.2fKB\0\r" % (pctg, bar, kb))

        def end(self):
            sys.stdout.write("\n")


class ModUpdater(object):

    MOD_JSON = "mod-list.json"


    def __init__(self, username, token,
                server="https://mods.factorio.com",
                api_path="/api/mods",
                mods_path=os.path.join(".", "mods"),
                logger=logging):
        """
        Create a ModUpdater object.

        :param username:  Forum account name
        :param token:     Forum login token/password
        :param server:    URI for the server [https://mods.factorio.com]
        :param api_path:  Server-relative path to the mods query API [/api/mods]
        :param mods_path: Path to the mods directory [./mods]
        :param logger:    Use a specific logging entity [logging]
        """
        self.username  = username
        self.token     = token
        self.server    = server.rstrip('/')
        self.api_path  = api_path
        self.mods_path = mods_path
        self.mods      = None
        self.mod_infos = None
        self.old_mods  = {}
        self.updates   = []
        self.logger    = logger

        # Check that the mods path exists.
        if not os.access(self.mods_path, os.W_OK):
            raise ValueError("mods_path is not writable: \"%s\"" % self.mods_path)

        # Create a session for our requests
        self._session = requests.Session()

        # Regex for matching mod names and extracting version strings.
        self._modname_match = re.compile('^(.*)_([0-9\.]+)\.zip').match


    def _get_local_mods(self):
        """ Locate local mods. """

        self.logger.debug("Fetching local mod list")
        modlist_path = os.path.join(self.mods_path, self.MOD_JSON)
        if not os.path.exists(modlist_path):
            raise RuntimeError("Missing mod list: %s" % modlist_path)

        if not os.access(modlist_path, os.R_OK | os.W_OK):
            raise RuntimeError("Insufficient access permissions: %s" % modlist_path)

        mod_info = json.loads(open(modlist_path, "r").read())
        if not mod_info or not 'mods' in mod_info:
            self.logger.debug("No local mods.")
            return

        self.mods = [m['name'] for m in mod_info['mods']]
        self.logger.debug("Mods: %s", ', '.join(self.mods))


    def _get_remote_info(self):
        """
        Returns information from the MOD api on a list of modules.

        :return:          'results' element of the return data
        """

        query_uri = self.server + self.api_path
        request_data = {
            'page_size': 'max',
            'namelist':  sorted(self.mods),
        }

        req = requests.Request("GET", query_uri, params=request_data).prepare()
        self.logger.debug("Fetching mod info: %s", req.url)
        resp = self._session.send(req)

        self.mod_infos = resp.json()['results']


    def _check_mod_out_of_date(self, mod_name, mod_vers):

        old_versions = []

        mod_glob = "%s_*.zip" % mod_name
        mod_glob_path = os.path.join(self.mods_path, mod_glob)
        for filepath in glob.glob(mod_glob_path):
            old_match = self._modname_match(os.path.basename(filepath))
            if not old_match:
                continue
            old_name, old_vers = old_match.group(1, 2)
            if old_name != mod_name:
                continue
            if LooseVersion(old_vers) >= mod_vers:
                msg = "%s local version (%s) is up-to-date (%s)."
                self.logger.debug(msg, mod_name, old_vers, mod_vers)
                return False
            old_versions.append(filepath)

        self.old_mods[mod_name] = old_versions

        return True


    def _check_out_of_date(self):

        self.logger.debug("Checking for out-of-date modules")
        for mod_info in self.mod_infos:

            new_release = max(mod_info['releases'], key=lambda r: LooseVersion(r['version']))
            release_filename = new_release['file_name']
            mod_match = self._modname_match(release_filename)
            if not mod_match:
                self.logger.debug("Cannot parse '%s' for mod version", release_filename)
                continue

            mod_name = mod_info['mod_name'] = mod_match.group(1)
            mod_vers = mod_info['mod_vers'] = LooseVersion(mod_match.group(2))

            if not self._check_mod_out_of_date(mod_name, mod_vers):
                continue

            mod_info.update(new_release)
            self.logger.info("%s needs updating", release_filename)
            self.updates.append(mod_info)


    def check_for_updates(self):
        # Find out what local mods we have.
        self._get_local_mods()
        if not self.mods:
            print("No local mods.")
            return False

        # Get a list of the remote info for those mods.
        self._get_remote_info()
        if not self.mod_infos:
            print("No mods on the remote server.")
            return False

        # Determine which mods are out of date.
        self._check_out_of_date()
        if not self.updates:
            print("Mods are up-to date.")
            return False

        return True


    def do_updates(self, leave_old_versions, dry_run=False):
        """
        Fetches binaries for each of the listed mods.

        :param leave_old_versions: If False, old versions of files are deleted.
        :param dry_run: If True, non-destructive run only.
        :return:          Iterable of downloaded files.
        """
        for mod_info in self.updates:

            mod_name     = mod_info['mod_name']
            mod_version  = mod_info['mod_vers']

            self.logger.info("Downloading %s v%s", mod_name, mod_version)

            # Where we'll store the finished download
            mod_path     = mod_info['download_url']
            mod_filename = mod_info['file_name']
            dl_path      = os.path.join(self.mods_path, mod_filename)

            # Where we'll download it to (temporary file)
            tmp_filename = ".mod_%s.dl" % (mod_filename)
            tmp_path     = os.path.join(self.mods_path, tmp_filename)

            uri = self.server + mod_path
            req = requests.Request("GET", uri).prepare()
            self.logger.debug("Requesting: %s => %s => %s", req.url, tmp_path, dl_path)

            try:
                with open(tmp_path, "wb") as outfh:
                    resp = self._session.send(req, stream=True)
                    if resp.status_code != 200:
                        raise ValueError("Could not download %s" % uri)

                    # Form a progress bar to report the download status.
                    file_size = int(resp.headers['Content-Length'])
                    pb = ProgressBar(mod_filename, file_size)

                    # Read the file a few pages at a time.
                    chunk_size = 4 * resource.getpagesize()
                    bytes_read = 0
                    for chunk in resp.iter_content(chunk_size=chunk_size, decode_unicode=False):
                        outfh.write(chunk)
                        bytes_read += len(chunk)
                        pb.update(bytes_read)

                self.logger.debug("Rename %s => %s", tmp_path, dl_path)
                if not dry_run:
                    os.rename(tmp_path, dl_path)
                else:
                    self.logger.debug("# mv \"%s\" \"%s\"", tmp_path, dl_path)

            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                pb.end()

            if not leave_old_versions:
                old_files = self.old_mods.get(mod_name, [])
                for old_file in old_files:
                    self.logger.debug("Removing old %s version: %s", mod_name, old_file)
                    try:
                        if not dry_run:
                            os.unlink(old_file)
                        else:
                            self.logger.debug("# rm \"%s\"", old_file)
                    except OSError:
                        pass


def parse_arguments(argv):

    parser = argparse.ArgumentParser("Mod Updater")

    parser.add_argument("--username", "-u", type=str,
            help="Username for the mod site", required=True)
    parser.add_argument("--token",    "-t", type=str,
            help="Auth token for the username", required=True)

    parser.add_argument("--check", "-C", action="store_true",
            help="Test for updates only, don't download anything.")
    parser.add_argument("--dry-run", "-n", action="store_true",
            dest="dry_run",
            help="Perform a dry-run only.")
    parser.add_argument("--leave-old", "-L", action="store_true",
            dest="leave_old_mods",
            help="Leave (don't delete) old versions of mod files")
    parser.add_argument("--verbose", "-v", action="store_true",
            help="Increase output verbosity.")

    return parser.parse_args(argv)


def main(argv):

    args = parse_arguments(argv)
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    updater = ModUpdater(args.username, args.token)
    updates = updater.check_for_updates()
    if not updates:
        return True
    if args.check:
        return False

    updater.do_updates(dry_run=args.dry_run, leave_old_versions=args.leave_old_mods)

    return True

if __name__ == "__main__":
    if not main(sys.argv[1:]):
        sys.exit(1)

