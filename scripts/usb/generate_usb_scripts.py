data = {"Australia": {
            "alpha2": "au",
            "exists": False,
            "slug": "australia"
        },
        "Austria": {
            "alpha2": "at",
            "exists": False,
            "slug": "austria"
        },
        "Brazil": {
            "alpha2": "br",
            "exists": False,
            "slug": "brazil"
        },
        "Bulgaria": {
            "alpha2": "bg",
            "exists": False,
            "slug": "bulgaria"
        },
        "Canada": {
            "alpha2": "CA",
            "exists": False,
            "slug": "canada"
        },
        "China": {
            "alpha2": "cn",
            "exists": False,
            "slug": "china"
        },
        "Chinese Taipei": {
            "alpha2": "tw",
            "exists": False,
            "slug": "chinese-taipei"
        },
        "Croatia": {
            "alpha2": "hr",
            "exists": False,
            "slug": "croatia"
        },
        "Czechia": {
            "alpha2": "cz",
            "exists": False,
            "slug": "czech-republic"
        },
        "Georgia": {
            "alpha2": "ge",
            "exists": False,
            "slug": "georgia"
        },
        "Germany": {
            "alpha2": "de",
            "exists": False,
            "slug": "germany"
        },
        "Greece": {
            "alpha2": "gr",
            "exists": False,
            "slug": "greece"
        },
        "Hong Kong": {
            "alpha2": "hk",
            "exists": False,
            "slug": "hong-kong"
        },
        "Hungary": {
            "alpha2": "hu",
            "exists": False,
            "slug": "hungary"
        },
        "India": {
            "alpha2": "in",
            "exists": False,
            "slug": "india"
        },
        "Iran": {
            "alpha2": "ir",
            "exists": False,
            "slug": "iran"
        },
        "Italy": {
            "alpha2": "it",
            "exists": False,
            "slug": "italy"
        },
        "Kazakhstan": {
            "alpha2": "kz",
            "exists": False,
            "slug": "kazakhstan"
        },
        "Korea": {
            "alpha2": "kr",
            "exists": False,
            "slug": "korea"
        },
        "Macao": {
            "alpha2": "mo",
            "exists": False,
            "slug": "macao"
        },
        "Mexico": {
            "alpha2": "MX",
            "exists": False,
            "slug": "mexico"
        },
        "Nepal": {
            "alpha2": "np",
            "exists": False,
            "slug": "nepal"
        },
        "New Zealand": {
            "alpha2": "nz",
            "exists": False,
            "slug": "new-zealand"
        },
        "Nigeria": {
            "alpha2": "ng",
            "exists": False,
            "slug": "nigeria"
        },
        "Pakistan": {
            "alpha2": "pk",
            "exists": False,
            "slug": "pakistan"
        },
        "Poland": {
            "alpha2": "pl",
            "exists": False,
            "slug": "poland"
        },
        "Romania": {
            "alpha2": "ro",
            "exists": False,
            "slug": "romania"
        },
        "Serbia": {
            "alpha2": "RS",
            "exists": False,
            "slug": "serbia"
        },
        "Singapore": {
            "alpha2": "sg",
            "exists": False,
            "slug": "singapore"
        },
        "Slovakia": {
            "alpha2": "sk",
            "exists": False,
            "slug": "slovakia"
        },
        "Slovenia": {
            "alpha2": "si",
            "exists": False,
            "slug": "slovenia"
        },
        "South Africa": {
            "alpha2": "ZA",
            "exists": False,
            "slug": "south-africa"
        },
        "Sweden": {
            "alpha2": "se",
            "exists": False,
            "slug": "sweden"
        },
        "Switzerland": {
            "alpha2": "ch",
            "exists": False,
            "slug": "switzerland"
        },
        "Thailand": {
            "alpha2": "TH",
            "exists": False,
            "slug": "thailand"
        },
        "Turkiye": {
            "alpha2": "tr",
            "exists": False,
            "slug": "turkiye"
        },
        "USA": {
            "alpha2": "us",
            "exists": False,
            "slug": "usa"
        },
        "Uganda": {
            "alpha2": "ug",
            "exists": False,
            "slug": "uganda"
        },
        "Ukraine": {
            "alpha2": "ua",
            "exists": False,
            "slug": "ukraine"
        },
        "United Kingdom": {
            "alpha2": "gb",
            "exists": False,
            "slug": "united-kingdom"
        },
        "Uzbekistan": {
            "alpha2": "uz",
            "exists": False,
            "slug": "uzbekistan"
        }
    }


fullnames = {el["alpha2"].lower():na for na,el in data.items()}

fmt = open("formatting.sh", "w")

mkd = open("mkdirs.sh", "w")

fst = open("custom.fstab", "w")

ids = []

with open("usbid_country.map") as f:
    for line in f:
        parts = line.strip().split(" ")
        cn=  fullnames[parts[1].lower()]
        print(parts,cn.upper(), len(cn))
        fmt.write(f'if [ -e /dev/disk/by-id/{parts[0]}-part1 ]; then mkfs.vfat -n "{cn.upper()[:11]}" /dev/disk/by-id/{parts[0]}-part1; fi\n')
        ids.append(parts[0])
        dirn = cn.replace(' ','_').lower()
        mkd.write(f"mkdir -p mnt/{dirn}\n")
        fst.write(f'/dev/disk/by-id/{parts[0]}-part1    /home/felix/nlogn/iypt/GLUE/scripts/usb/mnt/{dirn}  auto    ro,user 0   0\n')

print(len(ids), len(set(ids)))
fmt.close()
mkd.close()
fst.close()
