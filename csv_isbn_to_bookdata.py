import csv
import requests
import json
import pathlib # for globbing
import os
from difflib import SequenceMatcher
from googlesearch import search

HEADER = ['title', 'authors', 'year', 'isbn', 'isbn source file']

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

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

def google_book_json_to_data(jres, original=None):
  if jres is None or jres.get('totalItems', 0) == 0 or 'items' not in jres:
    print(f'[GOOGLE] No bookdata found for isbn. ')
    return None
  if len(jres['items']) == 1:
    jres = jres['items'][0]
  else:
    matched = False
    for i, item in enumerate(jres['items']):
      if similar(item['volumeInfo']['title'], original[0]) > 0.8:
        jres = item
        matched = True
    if not matched:
      print(f'Warning: multiple items found for this ISBN, and no similar title. Which one do you use?')
      for i, item in enumerate(jres['items']):
        print(f'{i}: {item["volumeInfo"]["title"]}')
      choice = int(input())
      jres = jres['items'][choice] if choice in range(len(jres['items'])) else None
  if jres is None: return None

  volume_info = jres['volumeInfo']
  title = get_or_else(volume_info, 'title', '???')
  authors = ', '.join(get_or_else(volume_info, 'authors', '???'))
  year = get_or_else(volume_info, 'publishedDate', '???')
  return [title, authors, year]

def complete_csv(csvfile):
  print(f'Completing csv file {csvfile}')
  # print('Enter number of row to start with: ')
  #start_input = input()
  start = args.startline # int(start_input) if start_input.isdigit() else 1
  f = open(csvfile, 'r', newline='', encoding='utf-8-sig')
  data = list(csv.reader(f, delimiter='|'))
  f.close()
  skip = False
  ASK_FOR_SKIP_EVERY = 50
  with open(csvfile, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter='|', lineterminator='\n')
    if data[0] == HEADER: w.writerow(data[0]) # write header
    for i, line in enumerate(data[1 if data[0] == HEADER else 0:]): # skip header
      if i % ASK_FOR_SKIP_EVERY == 0 and not skip and i > start:
        print(f'[CONTROL] Processed other {ASK_FOR_SKIP_EVERY} rows. Do you want to skip the rest? (y/n)')
        skip = input() == 'y'
      if i < start or skip:
        w.writerow(line)
        continue
      print(f'[{i}] {line}')
      if line[0] != '???': 
        if args.check:
          isbn = line[3]
          if args.gsearch:
            gsearch = search(isbn, num_results=5, timeout=2) 
            any_similar = False
            for item in gsearch:
              if similar(line[0], item) > 0.3:
                any_similar = True
                # print(f'[CHECK] GSEARCH similarity above threshold for: {item}')
            if not any_similar:
              print(f'[CHECK] No similar title found on Google Search.\n{list(gsearch)}')
          jres = google_book_json_to_data(get_book_data_from_google(isbn), line) if args.google else None
          if jres is None or not args.google:
            print(f'[CHECK] No data selected. Rewriting original line.') 
            w.writerow(line)
            continue
          if not similar(jres[0], line[0]) > 0.8:
            print(f'[CHECK] Row {line} has a title that is not similar to the one found on Google Books: {jres[0]}')
            print(f'[CHECK] Do you wanna replace it? (y/n)')
            replace = input()
            if replace == 'y':
              title, authors, year = jres
              isbn = line[3]
              isbn_filename = line[4]
              w.writerow([title, authors, year, isbn, isbn_filename])
            else:
              print(f'[CHECK] Keeping the original title. ')
              w.writerow(line)
          else:
            print(f'[CHECK] Similar title. Rewriting line. ')
            w.writerow(line)
        else:
          w.writerow(line)
      else:
        print(f'[ROW] Completing row {line}')
        isbn = line[3]
        jres = get_book_data_from_google(isbn)
        jres = google_book_json_to_data(jres)
        if jres is None: 
          w.writerow(line)
          print(line)
        else:
          title, authors, year = jres
          isbn = line[3]
          isbn_filename = line[4]
          w.writerow([title, authors, year, isbn, isbn_filename])
          print([title, authors, year, isbn, isbn_filename])


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("csvfiles", help="path to csv files", type=str, default="*.txt", nargs='*')
parser.add_argument("--check", help="only check if isbn data matches the right details", type=bool, default=False) # optional arg
parser.add_argument("--google", help="enable/disable googleapi check", type=bool, default=False) # optional arg
parser.add_argument("--gsearch", help="enable/disable google search check", type=bool, default=False) # optional arg
parser.add_argument("--startline", help="specify start line for check", type=int, default=1) # optional arg
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
print(f'basedir: {basedir}\nbasefile: {basefile}\nall_filepaths: {all_filepaths}\ngoogleapis.com: {args.google}')

if len(all_filepaths)==1 and str(all_filepaths[0]).endswith('.csv'):
  # a csv file has to be completed
  csv_to_complete = all_filepaths[0]
  complete_csv(csv_to_complete)
else:
  # a csv file has to be filled
  outf = open(args.outcsv, 'w', newline='')
  w = csv.writer(outf, delimiter='|', lineterminator='\n')
  # let's write the CSV header
  w.writerow(HEADER)
  for filepath in all_filepaths:
    get_book_data(filepath, w)
  outf.close()
