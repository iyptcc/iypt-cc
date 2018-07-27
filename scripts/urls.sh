# find apps cc -name "urls.py" | xargs cat | grep -o "^ *url(r'[^,]*" | grep -o "url(r'.*" | cut -c 6-

python manage.py show_urls | grep -v "^/admin" |grep -v "^/__debug__" | cut -f 3