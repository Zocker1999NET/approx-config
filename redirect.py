#!/usr/bin/env python3

# Imports
import argparse
import os
from pathlib import Path
import re
import requests
import sys
import tempfile

## Variables

# Mirrors with multiple addresses (like per country)
multi_mapping = [
    r"(ftp[0-9]*\.[a-z]+|deb)\.debian\.org",
    r"[a-z]+\.(archive|releases)\.ubuntu\.com",
]

# Regexs used
mapRegex = re.compile(r"^<tr><td><a href=\"(?P<new>[^\"]+)\">[^<>]+</a></td><td><a href=\"(?P<old>.*)\">http[^<>]*</a></td></tr>$")
allProtoRegex = re.compile(r"^[a-z+]+:/*(?!/)")
protoReplaceRegex = re.compile(r"^https?://")
lineReplaceRegex = re.compile(r"^\s*deb(-src)? ")

## Code

multi_mapping = [re.compile(x) for x in multi_mapping]

verboseLevel = 0

def verb(txt, add=0):
    global verboseLevel
    global verbose_mode
    if verbose_mode:
        print((" " * (verboseLevel * 4 + add)) + txt)

def verbLevel(num):
    global verboseLevel
    verboseLevel += num
    if verboseLevel < 0:
        verboseLevel = 0

def splitDomainPath(url):
    if "/" in url:
        domain, path = url.split('/', 1)
        return domain, '/' + path
    else:
        return url, ''

def removeProtocol(url):
    return allProtoRegex.sub("", url)

def remove_slash_suffix(url):
    # Removes slash suffix so that also urls in sources without suffix will be matched
    return url[:-1] if url.endswith('/') else url

def discoverMap(server):
    global mapRegex
    # Request approx server
    res = requests.get(server)
    # Extract url_map
    url_map = {}
    for line in res.text.split('\n'):
        match = mapRegex.match(line)
        if match:
            url_map[remove_slash_suffix(match.group('old'))] = server + '/' + remove_slash_suffix(match.group('new'))
    return url_map

def url_to_regex(url, multi_mapping=multi_mapping):
    # Check if old path is prepend by https?://
    if protoReplaceRegex.match(url):
        url = removeProtocol(url)
        domain, path = splitDomainPath(url)
        # Check if domain is given in multi_mapping
        for m in multi_mapping:
            if m.match(domain):
                # If given exchange with multi mapped regex
                url_pattern = m.sub(m.pattern, domain) + re.escape(path)
                break
        else:
            url_pattern = re.escape(url)
        # Prefix protocol again
        return r"https?://" + url_pattern
    else:
        return re.escape(url)

def modifyMap(d):
    return {re.compile(url_to_regex(old)): new for old, new in d.items()}

def isDebLine(line):
    return lineReplaceRegex.search(line) is not None

def checkFile(file, map):
    global write_mode
    verb(("Run replacements on" if write_mode else "Check") + f" {file}:")
    verbLevel(1)
    if write_mode:
        newFile = tempfile.NamedTemporaryFile(mode="w", delete=False)
    changed = False
    for line in open(file, "r"):
        line = line[:-1]
        if isDebLine(line):
            for old_url, new_url in map.items():
                if old_url.search(line):
                    changed = True
                    new_line = old_url.sub(new_url, line)
                    verb(f"{line}")
                    verb(f"-> {new_line}", add=-3)
                    line = new_line
                    break
            else:
                verb(f"= {line}", add=-2)
        if write_mode:
            newFile.write(line + "\n")
    if write_mode:
        origFilePath = Path(file)
        backFilePath = Path(file + ".save")
        newFilePath = Path(newFile.name)
        newFile.close()
        newFilePath.chmod(0o644)
        if changed:
            origFilePath.replace(backFilePath)
            newFilePath.rename(origFilePath)
    verbLevel(-1)

def main(argv):
    global mirror_mode
    global verbose_mode
    global write_mode
    # Parse arguments
    parser = argparse.ArgumentParser(description="Redirects apt sources to a given approx cache if cached by approx. Only files ending with .list in sources.list.d will be changed.")
    parser.add_argument('host', help="The URL of the approx cache, uses http:// if protocol is omitted")
    parser.add_argument('-c', '--confirm', action='store_true', dest='confirm', help="Does rewrite the source files to redirect to approx, does require run as root")
    parser.add_argument('-m', '--mirror', action='store_true', dest='use_mirror', help="Uses mirror lists to allow falling back to direct connection")
    parser.add_argument('-p', '--path', dest='path', default='/etc/apt', type=Path, help="Configuration directory of apt containing sources.list files, defaults to /etc/apt")
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help="Displays debug information")
    args = parser.parse_args(argv)
    # Check server host
    if not allProtoRegex.match(args.host):
        args.host = "http://" + args.host
    # Store configuration in global vars
    mirror_mode = args.use_mirror
    verbose_mode = args.verbose
    write_mode = args.confirm
    # Retrieve repository map
    verb(f"Connect to {args.host} to retrieve repository list")
    repo_map = modifyMap(discoverMap(args.host))
    verb("Found following repositories:")
    verbLevel(1)
    for k, v in repo_map.items():
        verb(k.pattern)
    verbLevel(-1)
    # Check for sources files
    file_list = [args.path / 'sources.list'] + [file for file in (args.path / 'sources.list.d').rglob('*.list') if file.is_file()]
    for file in file_list:
        if file.exists():
            checkFile(str(file.resolve()), repo_map)

if __name__ == '__main__':
    main(sys.argv[1:])
