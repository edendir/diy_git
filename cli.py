# File for parsing and processing command line arguments for the git-like CLI
import argparse
import os
import sys

from . import base
from . import data

def main():
    args = parse_args()
    args.func(args)

def parse_args():
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest="command")
    commands.required = True

    init_parser = commands.add_parser("init", help="Initialize a new repository")
    init_parser.set_defaults(func=init)

    hash_object_parser = commands.add_parser('hash-object')
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument('file', help='File to hash')

    cat_file_parser = commands.add_parser('cat_file')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument('object', help='Object to get')

    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=base.write_tree)

    read_tree_parser = commands.add_parser('read-tree')
    read_tree_parser.set_defaults(func=base.read_tree)
    read_tree_parser.add_argument('tree', help='Tree to read')

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