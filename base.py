import itertools
import operator
import os
import string

from collections import deque, namedtuple
from . import data
from . import diff

def init():
    data.init()
    data.update_ref('HEAD', data.RefValue(symbolic=True, value='refs/heads/master'))

def write_tree(directory='.'):
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            full = f'{directory}/{entry.name}'
            if is_ignored(full):
                continue
            if entry.is_file(follow_symlinks=False):
                type_ = 'blob'
                with open(full, 'rb') as f:
                    oid = data.hash_object(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type_ = 'tree'
                oid = write_tree(full)
            entries.append((entry.name, oid, type_))
    tree = ''.join (f'{type_} {oid} {name}\n' for name, oid, type_ in sorted(entries))
    
    return data.hash_object (tree.encode(), 'tree')

# Iterate over tree entries to tokenizw and give string values
def _iter_tree_entries(oid):
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ', 2)
        yield type_, oid, name

# Get the tree entries and return a dictionary with paths as keys and oids as values
def get_tree(oid, base_path=''):
    result = {}
    for type_, oid, name in _iter_tree_entries(oid):
        assert '/' not in name
        assert name not in ('.', '..')
        path = base_path + name
        if type_ == 'blob':
            result[path] = oid
        elif type_ == 'tree':
            result.update(get_tree(oid, f'{path}/'))
        else:
            assert False, f'Unknown tree entry {type_}'
    return result

# Get the current working tree
def get_working_tree():
    result = {}
    for root, _, filenames in os.walk('.'):
        for name in filenames:
            path = os.path.relpath(f'{root}/{name}')
            if is_ignored(path) or not os.path.isfile(path):
                continue
            with open(path, 'rb') as f:
                result[path] = data.hash_object(f.read())
    return result

# Empty the current directory to prep for writing the tree
def _empty_current_directory():
    for root, dirnames, filenames in os.walk('.', topdown=False):
        for name in filenames:
            path = os.path.relpath(f'{root}/{name}')
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)
        for dirname in dirnames:
            path = os.path.relpath(f'{root}/{dirname}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                # Delete might fail if directory contains ignored files
                pass

# Read the tree and write the files to disk
def read_tree(tree_oid):
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, pase_path='./').items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object(oid))

def read_tree_merged(t_base, t_HEAD, t_other):
    _empty_current_directory()
    for path, blob in diff.merge_trees(get_tree(t_base), get_tree(t_HEAD), get_tree(t_other)).items():
        os.makedirs(f'./{os.path.dirname(path)}', exist_ok=True)
        with open(path, 'wb') as f:
            f.write(blob)
        

# Commit the current tree to the repository
def commit(message):
    commit = f'tree {write_tree()}\n'
    
    HEAD = data.get_ref('HEAD').value
    if HEAD:
        commit += f'parent {HEAD} \n'
    MERGE_HEAD = data.get_ref('MERGE_HEAD').value
    if MERGE_HEAD:
        commit += f'parent {MERGE_HEAD} \n'
        data.delete_ref('MERGE_HEAD', deref=False)
    commit += f'\n{message}\n'

    oid = data.hash_object(commit.encode(), 'commit')

    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))
    
    return oid

# Checkout a commit by reading its tree and setting it as the HEAD
def checkout(name):
    oid = get_oid(name)
    commit = get_commit(oid)
    read_tree(commit.tree)
    if is_branch(name):
        HEAD = data.RefValue(symbolic=True, value=f'refs/heads/{name}')
    else:
        HEAD = data.RefValue(symbolic=False, value=oid)
    data.update_ref('HEAD', HEAD, deref=False)

# Reset HEAD
def reset(oid):
    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))

# Merge commits
def merge(other):
    HEAD = data.get_ref('HEAD').value
    assert HEAD
    merge_base = get_merge_base(other, HEAD)
    c_other = get_commit(other)

    # Handle fast-forward merge
    if merge_base == HEAD:
        read_tree(c_other.tree)
        data.update_ref('HEAD', data.RefValue(symbolic=False, value=other))
        print('Fast-forward merge, no commit needed')
        return

    data.update_ref('MERGE_HEAD', data.RefValue(symbolic=False, value=other))

    c_base = get_commit(merge_base)
    c_HEAD = get_commit(HEAD)
    read_tree_merged(c_base.tree, c_HEAD.tree, c_other.tree)
    print('Merged in working tree\nPlease commit to finish the merge')

def get_merge_base(oid1, oid2):
    parents1 = set(iter_commits_and_parents(oid1))
    for oid in iter_commits_and_parents(oid2):
        if oid in parents1:
            return oid

# Create a tag
def create_tag(name, oid):
    data.update_ref(f'tag/{name}', data.RefValue(symbolic=False, value=oid))

# Create a branch
def create_branch(name, oid):
    data.update_ref(f'heads/{name}', data.RefValue(symbolic=False, value=oid))

# Iterate over all branche names
def iter_branch_names():
    for refname, _ in data.iter_refs('refs/heads/'):
        yield os.path.relpath(refname, 'refs/heads/')

def is_branch(branch):
    return data.get_ref(f'refs/heads/{branch}').value is not None

def get_branch_name():
    HEAD = data.get_ref('HEAD', deref=False)
    if not HEAD.symbolic:
        return None
    HEAD = HEAD.value
    assert HEAD.startswith('refs/heads/')
    return os.path.relpath(HEAD, 'refs/heads/')

Commit = namedtuple('Commit', ['tree', 'parents', 'message'])

# Find a commit
def get_commit(oid):
    parents = []

    commit = data.get_object(oid, 'commit').decode()
    lines = iter(commit.splitlines())

    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(' ', 1)
        if key == 'tree':
            tree = value
        elif key == 'parent':
            parents.append(value)
        else:
            assert False, f'Unknown commit field {key}'

    message = '\n'.join(lines)
    return Commit(tree=tree, parents=parents, message=message)

def iter_commits_and_parents(oid):
    oids = deque(oids)
    visited = set()

    while oids:
        oid = oids.popleft()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid
    
        commit = get_commit(oid)
        # Return first parent next
        oids.extendleft(commit.parents[:1])
        # Return all other parents
        oids.extend(commit.parents[1:])


# Return name for a tag
def get_oid(name):
    if name == '@': name = 'HEAD'
    # Name is ref
    refs_to_try = [
        f'{name}',
        f'refs/{name}',
        f'refs/tags/{name}',
        f'refs/heads/{name}'
    ]
    for ref in refs_to_try:
        if data.get_ref(ref, deref=False).value:
            return data.get_ref(ref).value
    
    # Name is a commit ID
    is_hex = all(c in string.hexdigits for c in name)
    if is_hex and len(name) == 40:
        return name
    
    assert False, f'Unknown commit or tag {name}'

# Single function for ignoring paths
def is_ignored(path):
    return '.ugit' in path.split('/')