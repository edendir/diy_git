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
    