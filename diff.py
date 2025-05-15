import subprocess

from collections import defaultdict
from tempfile import NamedTemporaryFile as Temp

from . import data


def compare_trees(*trees):
    entries = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid

    for path, oids in entries.items():
        yield (path, *oids)

def iter_changed_files(t_from, t_to):
    for path, oid_from, oid_to in compare_trees(t_from, t_to):
        if oid_from != oid_to:
            action = ('new file' if not oid_from else
                     'deleted' if not oid_to else 'modified')
            yield path, action

def diff_trees(t_from, t_to):
    output = b''
    for path, oid_from, oid_to in compare_trees(t_from, t_to):
        if oid_from != oid_to:
            output += diff_blobs(oid_from, oid_to, path)

    return output

def diff_blobs(oid_from, oid_to, path='blob'):
    with Temp() as f_from, Temp() as f_to:
        for oid, f in ((oid_from, f_from), (oid_to, f_to)):
            if oid:
                f.write(data.get_object(oid))
                f.flush()
        with subprocess.Popen(
            ['diff', '-unified', '--show-c-function', 
                '--label', f'a/{path}', f_from.name,
                '--label', f'b/{path}', f_to.name],
            stdout=subprocess.PIPE) as proc:
            output = proc.communicate()
    
    return output

def merge_trees(t_base, t_HEAD, t_other):
    tree = {}
    for path, o_base, o_HEAD, o_other in compare_trees(t_base, t_HEAD, t_other):
        tree[path] = merge_blobs(o_base, o_HEAD, o_other)

    return tree

def merge_blobs(o_base, o_HEAD, o_other):
    with Temp() as f_base, Temp() as f_HEAD, Temp() as f_other:
        # Write the base, HEAD, and other blobs to temporary files
        for oid, f in ((o_base, f_base), (o_HEAD, f_HEAD), (o_other, f_other)):
            if oid:
                f.write(data.get_object(oid))
                f.flush()
        
        with subprocess.Popen(
            ['diff3', '-m',
                '-L', 'HEAD', f_HEAD.name,
                '-L', 'BASE', f_base.name,
                '-L', 'MERGE_HEAD',  f_other.name,
                ],
            stdout=subprocess.PIPE) as proc:
            output, _ = proc.communicate()
            assert proc.returncode in (0, 1), f'diff3 failed with code {proc.returncode}'
        
        return output

