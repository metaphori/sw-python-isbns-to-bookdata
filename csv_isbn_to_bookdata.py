import csv
import requests
import json
import pathlib # for globbing
import os

def get_or_else(m, k, default):
  return m[k] if k in m else default

def get_book_data_from_openlibrary(isbn):
  resp = requests.get(base_url_openlib, 
                      params = {'bibkeys': 'ISBN:' + isbn, 
                                'jscmd': 'details', 
                                'format': 'json'
                                })
  jres = json.loads(resp.text)
  json.dumps(jres)
  return jres

def get_book_data_from_google(isbn):
  resp = requests.get(base_url_google, 
                      params = {'q': isbn })
  jres = json.loads(resp.text)
  json.dumps(jres)
  return jres
  #if jres.get('totalItems', 0) == 0:
  #  return None
  #else:
  #  return jres


def get_book_data(isbn_file, out):
  '''
  This function takes a csv file with a column of ISBNs and returns a csv file with the following columns:
  - title
  - authors
  - year
  - isbn
  Arguments:
  - isbn_file: str, path to csv file with ISBNs
  - out: str, path to output csv file
  '''
  isbn_filename = os.path.basename(isbn_file)
  with open(isbn_file, newline='', encoding='utf-8-sig') as f:
    r = csv.reader(f)
    for row in r:
      isbn = str(row[0])
      print('Row #' + str(r.line_num) + ' ' + str(row) + ' ; first item: ' + isbn)
      jres = get_book_data_from_openlibrary
      if not jres:
        out.writerow(['???', '???', '???', isbn, isbn_filename])
        pass
        # print("empty")
      else:
        #json.dumps(jres)
        details = jres['ISBN:' + str(row[0])]['details']
        title = details['title']
        authors = ', '.join([get_or_else(a, 'name', '???') for a in get_or_else(details, 'authors', 'unknown author')])
        year = get_or_else(details, 'publish_date', 'unknown year')
        isbn = get_or_else(details, 'isbn_13', get_or_else(details, 'isbn10', [isbn]))[0]
        print(title, authors, year, isbn)
        out.writerow([title, authors, year, isbn, isbn_filename])

def complete_csv(csvfile):
  f = open(csvfile, 'r', newline='', encoding='utf-8-sig')
  data = list(csv.reader(f, delimiter='|'))
  f.close()
  with open(csvfile, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter='|', lineterminator='\n')
    for line in data:
      if line[0] != '???': w.writerow(line)
      else:
        isbn = line[3]
        jres = get_book_data_from_google(isbn)
        if jres is None or jres.get('totalItems', 0) == 0 or 'items' not in jres: 
          w.writerow(line)
          print(line)
        else:
          jres = jres['items'][0]
          title = jres['volumeInfo']['title']
          authors = ', '.join(jres['volumeInfo']['authors'])
          year = jres['volumeInfo']['publishedDate']
          isbn = line[3]
          isbn_filename = line[4]
          w.writerow([title, authors, year, isbn, isbn_filename])
          print([title, authors, year, isbn, isbn_filename])


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("csvfiles", help="path to csv files", type=str, default="*.txt", nargs='*')
parser.add_argument("-outcsv", help="path to output csv file", type=str, default="books.csv", required=False)
parser.add_argument("-v", "--verbosity", help="increase output verbosity", action="store_true") # optional arg
args = parser.parse_args()

base_url_google = 'https://www.googleapis.com/books/v1/volumes' # 'https://www.googleapis.com/books/v1/volumes?q=' 
base_url_openlib = 'https://openlibrary.org/api/books'
# api_path = 'books?bibkeys=ISBN:{0}&jscmd=details&format=json'

if len(args.csvfiles) > 1:
  basedir = os.path.abspath(os.path.dirname(args.csvfiles[0]))
  basefile = os.path.basename(args.csvfiles[0])
  all_filepaths = [pathlib.Path(os.path.join(basedir,f)) for f in args.csvfiles]
else:
  args.csvfiles = args.csvfiles[0] 
  basedir = os.path.abspath(os.path.dirname(args.csvfiles))
  basefile = os.path.basename(args.csvfiles)
  all_filepaths = list(pathlib.Path(basedir).glob(basefile))
print(f'basedir: {basedir}\nbasefile: {basefile}\nall_filepaths: {all_filepaths}')

if len(all_filepaths)==1 and str(all_filepaths[0]).endswith('.csv'):
  # a csv file has to be completed
  csv_to_complete = all_filepaths[0]
  complete_csv(csv_to_complete)
else:
  # a csv file has to be filled
  outf = open(args.outcsv, 'w', newline='')
  w = csv.writer(outf, delimiter='|', lineterminator='\n')
  # let's write the CSV header
  w.writerow(['title', 'authors', 'year', 'isbn', 'isbn source file'])
  for filepath in all_filepaths:
    get_book_data(filepath, w)
  outf.close()
