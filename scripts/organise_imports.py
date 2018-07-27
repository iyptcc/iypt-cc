
import sys
import glob

from isort import SortImports

exclude = ["static", "migrations"]

paths = []
if len(sys.argv) > 1:
    paths += sys.argv[1:]
else:
    paths.append(".")
print(paths)

#files = [glob.glob("%s/**/*.py"%path, recursive=True) for path in paths]
files = [glob.glob(path, recursive=True) for path in paths]
flat_files = [item for sublist in files for item in sublist]

for file in flat_files[:]:
    ignore = False
    for ex in exclude:
        if file.find("/%s/"%ex) != -1:
            ignore = True
            break

    if ignore:
        continue

    #print("----------processing file -----------")
    #print(file)
    PREAMBLE = 'preamble'
    IMPORTS = 'imports'
    BODY = 'body'

    with open(file,"r") as f:

        print("-----process %s"%file)

        state = PREAMBLE

        preamble = []
        imports = []
        froms = []
        comments = []
        tail_comments = []
        body = []
        body_imports = []

        multiline = None
        multiline_to = None

        for idx, line in enumerate(f):
            stripped = line.strip()

            #print("in line %d state:%s : %s"%(idx, state, stripped))

            new_state = state

            if state == PREAMBLE:
                if stripped.startswith('#'):
                    # # preamble
                    preamble.append(line)
                else:
                    # """ preamble
                    if idx == 0:
                        if not stripped.startswith('"""'):
                            state = IMPORTS
                            new_state = IMPORTS
                        else:
                            preamble.append(line)
                    else:
                        if stripped.find('"""') == -1:
                            preamble.append(line)
                        else:
                            preamble.append(line)
                            new_state = IMPORTS

            if state == IMPORTS:
                if stripped == "":
                    pass
                elif stripped[0] == '#':
                    # comment
                    comments.append(line)
                elif stripped.startswith("from ") and not stripped.endswith('\\'):
                    # single line from import
                    froms.append(line)
                elif stripped.startswith("import ") and not stripped.endswith('\\'):
                    # single line import
                    imports.append(line)
                elif stripped.startswith("from ") and stripped.endswith('\\'):
                    # start of multiline from
                    multiline = [line]
                    multiline_to = froms
                elif stripped.startswith("import ") and stripped.endswith('\\'):
                    # start of multiline import
                    multiline = [line]
                    multiline_to = imports
                elif multiline:
                    if stripped.endswith('\\'):
                        # continue multiline input
                        multiline.append(line)
                    else:
                        # last multiline input
                        multiline.append(line)
                        multiline_to.append("".join(multiline))
                        multiline = None
                else:
                    # first line of main code
                    state = BODY
                    new_state = BODY

                if stripped != "":
                    if stripped[0] == '#':
                        #print("gather comment")
                        tail_comments.append(line)
                    elif state == IMPORTS:
                        #print("reset comment")
                        tail_comments = []

            if state == BODY:
                body.append(line)

                if stripped.startswith("from ") or stripped.startswith("import "):
                    body_imports.append(line)

            state = new_state

        class Dump():
            def writelines(self,lines):
                pass
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        #with open("%s.mylint"%file,"w") as w:
        with Dump() as w:

            if len(preamble):
                w.writelines(preamble)

            import_comments = [c for c in comments if c not in tail_comments]

            w.writelines(imports)
            #print("".join([l[7:] for l in imports]))
            #print("".join(sorted(imports, key=lambda x:x[8:])))

            #print("".join(froms))

            #for f in froms:
            #    module = f.split("import")[0][5:].strip()

            fromset = set(froms)

            django_froms = list(filter(lambda x:x.startswith("from django ") or x.startswith("from django."),froms))
            apps_froms = list(filter(lambda x:x.startswith("from apps."),froms))
            rel_froms = list(filter(lambda x:x.startswith("from ."),froms))
            fromset -= set(django_froms)
            fromset -= set(apps_froms)
            fromset -= set(rel_froms)

            #print(list(fromset))
            #print(django_froms)
            #print(apps_froms)
            #print(rel_froms)

            #print("".join(imports+froms))

            #new_contents = SortImports(file_contents="".join(imports+froms)).output
            #print("formated:")
            #print(new_contents)


            w.writelines(froms)

            if len(import_comments):
                print(file)
                print("comments in imports")
                print("".join(import_comments))

            w.writelines(tail_comments)

            w.writelines(body)

            body_toplevel = [i for i in body_imports if i[0]!=' ']
            if len(body_toplevel):
                print(file)
                print("top level body imports:")
                print("".join(body_toplevel))

