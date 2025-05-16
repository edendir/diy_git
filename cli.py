# File for parsing and processing command line arguments for the git-like CLI
import argparse
import os
import subprocess
import sys
import textwrap

from . import base
from . import data
from . import diff

def main():
    with data.change_git_dir('.'):
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

    diff_parser = commands.add_parser('diff')
    diff_parser.set_defaults(func=diff)
    diff_parser.add_argument('from_oid', default='@', type=oid, help='From commit ID', nargs='?')

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

    merge_parser = commands.add_parser('merge')
    merge_parser.set_defaults(func=merge)
    merge_parser.add_argument('commit', type=oid, help='Commit ID to merge')

    merge_base_parser = commands.add_parser('merge-base')
    merge_base_parser.set_defaults(func=merge_base)
    merge_base_parser.add_argument('commit1', type=oid, help='First commit ID')
    merge_base_parser.add_argument('commit2', type=oid, help='Second commit ID')

    fetch_parser = commands.add_parser('fetch')
    fetch_parser.set_defaults(func=fetch)
    fetch_parser.add_argument('remote', help='Remote path to fetch from')

    push_parser = commands.add_parser('push')
    push_parser.set_defaults(func=push)
    push_parser.add_argument('remote', help='Remote path to push to')
    push_parser.add_argument('branch', help='Branch to push')

    add_parser = commands.add_parser('add')
    add_parser.set_defaults(func=add)
    add_parser.add_argument('files', nargs='+' help='Files to add')

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
    parent_tree = None
    if commit.parents:
        parent_tree = base.get_commit(commit.parents[0]).tree
    _print_commit(args.oid, commit)
    result = diff.diff_tree(
        base.get_tree(commit.parent_tree), base.get_tree(commit.tree)
    )
    print(result)

# Show the diff between working tree and a commit
def _diff(args):
    tree = args.commit and base.get_commit(args.commit).tree

    result = diff.diff_tree(base.get_tree(tree), base.get_working_tree())
    sys.stdout.flush()
    sys.stdout.buffer.write(result)

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
        for parent in commit.parents:
            dot += f'"{oid}" -> "{parent}"\n'
    
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

    MERGE_HEAD = data.get_ref('MERGE_HEAD').value
    if MERGE_HEAD:
        print(f'Merging with {MERGE_HEAD[:10]}')

    print('\nChanges to be committed:\n')
    HEAD_tree = HEAD and base.get_commit(HEAD).tree
    for path, action in diff.iter_changed_files(
        base.get_tree(HEAD_tree), base.get_working_tree()
    ):
        print(f'{action:>12}: {path}')

def reset(args):
    base.reset(args.oid)
    print(f'HEAD reset to {args.oid[:10]}')

def merge(args):
    base.merge(args.commit)
    print(f'Merged {args.commit[:10]} into HEAD')

def merge_base(args):
    print(base.get_merge_base(args.commit1, args.commit2))

def fetch(args):
    remote.fetch(args.remote)

def push(args):
    remote.push(args.remote, f'refs/heads/{args.branch}')

def add(args):
    base.add(args.files)