def _normal_capitalisation(name):
    name = name.replace("-", " ")
    parts = name.split(" ")
    for p in parts:
        if p in ["de", "von", "van"]:
            continue
        if len(p) > 1:
            if p[0].islower():
                return False
            for c in p[1:]:
                if c.isupper():
                    return False
    return True
