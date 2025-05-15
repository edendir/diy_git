# File for parsing and processing command line arguments for the git-like CLI
import argparse
import os
import subprocess
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

    show_parser = commands.add_parser('show')
    show_parser.set_defaults(func=show)
    show_parser.add_argument('object', default='@', type=oid, nargs='?', help='Object to show')

    commit_parser = commands.add_parser('commit')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('message', help='Commit message', required=True)

    log_parser = commands.add_parser('log')
    log_parser.set_defaults(func=log)
    log_parser.add_argument('oid', default='@', nargs='?', type=oid, help='Commit ID to show log for', default=None)

    checkout_parser = commands.add_parser('checkout')
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument('commit')

    tag_parser = commands.add_parser('tag')
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument('name', nargs='?', help='Tag name')
    tag_parser.add_argument('oid', default='@', type=oid, help='Commit ID to tag', nargs='?')

    branch_parser = commands.add_parser('branch')
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument('name', help='Branch name')
    branch_parser.add_argument('start_point', default='@', type=oid, help='Starting point for the branch', nargs='?')
    
    k_parser = commands.add_parser('k')
    k_parser.set_defaults(func=k)

    status_parser = commands.add_parser('status')
    status_parser.set_defaults(func=status)

    reset_parser = commands.add_parser('reset')
    reset_parser.set_defaults(func=reset)
    reset_parser.add_argument('oid', type=oid, help='Commit ID to reset to')

    return parser.parse_args()

# Initialize a new repository
def init(args):
    base.init()
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

# Print commit
def _print_commit(oid, commit, refs=None):
    refs_str = f' ({", ".join(refs)})' if refs else ''
    print(f'commit {oid}{refs_str}\n')
    print(textwrap.indent(commit.message, '    '))
    print('')

# Log the commits
def log(args):
    refs = {}
    for refname, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname)
    
    for oid in base.iter_commits_and_parents(args.oid):
        commit = base.get_commit(oid)
        _print_commit(oid, commit, refs.get(oid))

# Show an object
def show(args):
    if not args.oid:
        return
    commit = base.get_commit(args.oid)
    _print_commit(args.oid, commit)

# Checkout a commit
def checkout(args):
    base.checkout(args.commit)

# Create a tag
def tag(args):
    base.create_tag(args.name, args.oid)

#Create a branch
def branch(args):
    if not args.name:
        current = base.get_branch_name()
        for branch in base.iter_branch_names():
            prefix = '*' if branch == current else ' '
            print(f'{prefix} {branch}')
    else:
        base.create_branch(args.name, args.start_point)
        print(f'Created branch {args.name} at {args.start_point[:10]}')

# Visualize the commit graph
def k(args):
    dot = 'digraph commits {\n'
    oids = set()
    for refname, ref in data.iter_refs(deref=False):
        dot += f'"{refname}" [shape=note]\n'
        dot += f'"{refname}" -> "{ref.value}"\n'
        if not ref.symbolic:
            oids.add(ref.value)
    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [shape-box style=filled label="{oid[:10]}"]\n'
        if commit.parent:
            dot += f'"{oid}" -> "{commit.parent}"\n'
    
    dot += '}'
    print(dot)

    with subprocess.Popen(
            ['dot', '-Tgtk', '/dev/stdin'],
            stdin=subprocess.PIPE) as proc:
        proc.communicate(dot.encode())

def status(args):
    HEAD = base.get_oid('@')
    branch = base.get_branch_name()
    if branch:
        print(f'On branch {branch}')
    else:
        print(f'HEAD detached at {HEAD[:10]}')

def reset(args):
    base.reset(args.oid)
    print(f'HEAD reset to {args.oid[:10]}')