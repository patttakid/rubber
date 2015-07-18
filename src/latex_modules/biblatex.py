# This file is part of Rubber and thus covered by the GPL
# (c) Sebastian Reichel, 2014
"""
basic BibLaTeX support for Rubber
"""

import sys
from os import getenv
from os.path import join, exists, getmtime
from rubber.util import parse_keyval, md5_file
from rubber import _, msg
from string import split

def setup (document, context):
    global doc, bibinputs, bbl, bblhash, bcf, bcfhash
    doc = document

    opt = context['opt'] or None
    options = parse_keyval(opt) if opt != None else {}

    if "backend" in options and options["backend"] != "biber":
        msg.warn (_ ("rubber's biblatex plugin only supports the biber backend"), pkg="biblatex")

    doc.hook_macro('addbibresource', 'oa', hook_bibresource)
    doc.hook_macro('addglobalbib', 'oa', hook_bibresource)
    doc.hook_macro('addsectionbib', 'oa', hook_bibresource)

    # Try current directory, then path to tex file, then BIBINPUTS.
    bibinputs = [doc.vars ["cwd"], doc.vars ["path"]]
    bibinputs.extend (getenv ("BIBINPUTS", "").split (":"))

    # Erase the two default hooks triggering bibtex module.
    doc.hook_macro('bibliographystyle', 'a', hook_bibliographystyle)
    doc.hook_macro('bibliography', 'a', hook_bibliography)

    bcf = doc.target + ".bcf"
    bcfhash = None
    bbl = doc.target + ".bbl"
    bblhash = md5_file(bbl)

def hook_bibresource (loc, opt, file):
    options = parse_keyval(opt) if opt != None else {}

    # If the file name looks like it contains a control sequence
    # or a macro argument, forget about this resource.
    if file.find('\\') > 0 or file.find('#') > 0:
        return

    # skip remote resources
    if 'location' in options and options['location'] == 'remote':
        return

    for bibpath in bibinputs:
        bibfile = join(bibpath, file)
        if exists(bibfile):
            doc.add_source(bibfile)
            return

    msg.error (_ ("cannot find %s") % file, pkg="biblatex")
    sys.exit(2)

def hook_bibliography (loc, files):
    for bib in split(files, ","):
        hook_bibresource(loc, None, bib.strip()+".bib")

def hook_bibliographystyle (loc, bibs):
    msg.warn (_ ("\\usepackage{biblatex} incompatible with \\bibliographystyle"), pkg="biblatex")

def biber_needed():
    if not exists(bcf):
        msg.info (_ ("bcf file has not been generated by biblatex!"), pkg="biblatex")
        return False
    return (not exists (bbl)
            or (getmtime (bbl) <= getmtime (bcf)
                and bcfhash != md5_file (bcf)))

def run_biber():
    global bcfhash
    global bblhash
    msg.progress (_ ("running biber on %s") % msg.simplify(bcf), pkg="biblatex");
    if doc.env.execute (["biber", bcf], { "BIBINPUTS":":".join (bibinputs) }):
        msg.info (_ ("There were errors making the bibliography."), pkg="biblatex")
        return False
    bcfhash = md5_file(bcf)
    newbblhash = md5_file(bbl)
    if bblhash != newbblhash:
        bblhash = newbblhash
        doc.must_compile = 1
    else:
        msg.info (_ ("bbl file stayed the same, no recompilation needed."), pkg="biblatex")
    return True

def post_compile ():
    if not biber_needed():
        return True
    return run_biber()

def clean ():
    # generated by the biblatex module
    doc.remove_suffixes([".run.xml", ".bcf"])
    # generated by biber
    doc.remove_suffixes([".bbl", ".blg"])
