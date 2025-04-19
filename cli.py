# File for parsing and processing command line arguments for the git-like CLI
import argparse
import os
import sys
import textwrap

from . import base
from . import data

def main():
    args = parse_args()
    args.func(args)

def parse_args():
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest="command")
    commands.required = True

    oid = base.get_oid

    init_parser = commands.add_parser("init", help="Initialize a new repository")
    init_parser.set_defaults(func=init)

    hash_object_parser = commands.add_parser('hash-object')
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument('file', help='File to hash')

    cat_file_parser = commands.add_parser('cat_file')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument('object', type=oid, help='Object to get')

    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=base.write_tree)

    read_tree_parser = commands.add_parser('read-tree')
    read_tree_parser.set_defaults(func=base.read_tree)
    read_tree_parser.add_argument('tree', type=oid, help='Tree to read')

    commit_parser = commands.add_parser('commit')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('message', help='Commit message', required=True)

    log_parser = commands.add_parser('log')
    log_parser.set_defaults(func=log)
    log_parser.add_argument('oid', nargs='?', type=oid, help='Commit ID to show log for', default=None)

    checkout_parser = commands.add_parser('checkout')
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument('oid', type=oid, help='Commit ID to checkout')

    tag_parser = commands.add_parser('tag')
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument('name', help='Tag name')
    tag_parser.add_argument('oid', type=oid, help='Commit ID to tag', nargs='?')

    return parser.parse_args()

# Initialize a new repository
def init(args):
    data.init()
    print(f'Initializing a new repository in {os.getcwd()}/{data.GIT_DIR}')
    
# Hash an object
def hash_object(args):
    with open(args.file, 'rb') as f:
        print(data.hash_object(f.read()))
    
# Get an object
def cat_file(args):
    sys.sdtout.flush()
    sys.stdout.buffer.write(data.get_object(args.object, expected=None))

# Create a new tree object
def write_tree(args):
    print(base.write_tree())
    
# Read a tree object
def read_tree(args):
    base.read_tree(args.tree)

# Commit the changes
def commit(args):
    print(base.commit(args.message))

# Log the commits
def log(args):
    oid = args.oid or data.get_ref('HEAD')
    while oid:
        commit = base.get_commit(oid)
        print(f'commit {oid}\n')
        print(textwrap.indent(commit.message, '    '))
        print('')
        oid = commit.parent

# Checkout a commit
def checkout(args):
    base.checkout(args.oid)
    print(f'Checked out {args.oid}')

# Create a tag
def tag(args):
    oid - args.oid or data.get_ref('HEAD')
    base.create_tag(args.name, oid)
