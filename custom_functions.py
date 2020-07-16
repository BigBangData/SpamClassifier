def get_data(spam, ham):

    import os
    import tarfile
    import requests
 
    if os.path.isdir('data'):
        pass
    else:
        os.mkdir('data')
        
    _head = 'http://spamassassin.apache.org/old/publiccorpus/'
    _ext = '.tar.bz2'
    
    _spam = ''.join([_head, spam, _ext])
    _ham = ''.join([_head, ham, _ext])
    
    
    for _url in _spam, _ham:
        
        # extract dir name from _url
        _dir = _url.split('/')[len(_url.split('/'))-1].split('.')[0]
        _filepath = os.path.join('data', _dir)
        
        try:
            r = requests.get(_url)
            
            if r.status_code == 200:
                print('Downloading ' + _dir + '...')
            else:
                print('Request failed with error status code: ' + str(r.status_code) +'\n')
        except:
            print('Request error.\n')
            continue
        
        try:
            f = open(_filepath, 'wb')
            f.write(r.content)
            f.close()
            print('Saving data...')
        except:
            print('Failed writing to folders.\n')
            continue
        
        try:
            t = tarfile.open(_filepath, 'r:bz2')
            t.extractall('data')
            t.close()
            os.remove(_filepath)
            print('Extracting files...\n')
        except:
            print('Failed extracting files.\n')
            print(_filepath)
            continue

def get_data_if_needed(spam, ham, date):
    
    def get_date(emailtype):
        
        import os
        import datetime as dt
        
        uxtime = os.path.getmtime(os.path.join('data', emailtype))
        
        return(dt.datetime.fromtimestamp(uxtime).strftime('%Y%m%d'))
    
    import os 
    
    if (os.path.isdir(os.path.join('data', spam)) and get_date(spam) == date) \
    and (os.path.isdir(os.path.join('data', ham)) and get_date(ham) == date):
        print('Data successfully downloaded.')
    else: 
        _spam = ''.join([date, '_', spam])
        _ham = ''.join([date, '_', ham])
        get_data(_spam, _ham, date)
        
def extract_emails(_path, _names):

    def parse_emails(filename):
        
        import os
        import email
        import email.policy
        
        with open(os.path.join(_path, filename), 'rb') as fp:
            return(email.parser.BytesParser(policy=email.policy.default).parse(fp))
        
    return([parse_emails(filename=name) for name in _names])

def structures_counter(emails):
 
    def get_structure(email):

        payload = email.get_payload()

        if isinstance(payload, list):
            return "multipart({})".format(" | ".join([
                get_structure(sub_email)
                for sub_email in payload
            ]))
        else:
            return email.get_content_type()
        
    from collections import Counter
    
    
    structures = Counter()
    for email in emails:
        structure = get_structure(email)
        structures[structure] += 1
    return structures

import re
from html import unescape

def html_to_plaintext(html):
    text = re.sub('<head.*?>.*?</head>', '', html, flags=re.M | re.S | re.I)
    text = re.sub('<a\s.*?>', ' HYPERLINK ', text, flags=re.M | re.S | re.I)
    text = re.sub('<.*?>', '', text, flags=re.M | re.S)
    text = re.sub(r'(\s*\n)+', '\n', text, flags=re.M | re.S)
    return unescape(text)

def email_to_text(email):
    html = None
    for part in email.walk():
        ctype = part.get_content_type()
        if not ctype in ("text/plain", "text/html"):
            continue
        try:
            content = part.get_content()
        except: # in case of encoding issues
            content = str(part.get_payload())
        if ctype == "text/plain":
            return content
        else:
            html = content
    if html:
        return html_to_plaintext(html)

from sklearn.base import BaseEstimator, TransformerMixin

class EmailToWordCounterTransformer_ORIGINAL(BaseEstimator, TransformerMixin):

    def __init__(self, strip_headers=True, lower_case=True, remove_punctuation=True,
                 replace_urls=True, replace_numbers=True, remove_stopwords=False, stemming=True):
        self.strip_headers = strip_headers
        self.lower_case = lower_case
        self.remove_punctuation = remove_punctuation
        self.replace_urls = replace_urls
        self.replace_numbers = replace_numbers
        self.remove_stopwords = remove_stopwords
        self.stemming = stemming
        
    def fit(self, X, y=None):
        return self
    
    def transform(self, X, y=None):
        
        from collections import Counter
        import nltk
        from nltk.corpus import stopwords 
        from nltk.tokenize import word_tokenize
        import urlextract 
        import numpy as np
        
        X_transformed = []
        
        for email in X:
            text = email_to_text(email) or ""
            
            if self.lower_case:
                text = text.lower()
                
            if self.replace_urls:
                url_extractor = urlextract.URLExtract()
                urls = list(set(url_extractor.find_urls(text)))
                urls.sort(key=lambda url: len(url), reverse=True)
                for url in urls:
                    text = text.replace(url, " URL ")
                    
            if self.replace_numbers:
                text = re.sub(r'\d+(?:\.\d*(?:[eE]\d+))?', 'NUMBER', text)
                
            if self.remove_punctuation:
                text = re.sub(r'\W+', ' ', text, flags=re.M)
            
            if self.remove_stopwords:
                stop_words = set(stopwords.words("english"))
                word_tokens = word_tokenize(text)
                text = [word for word in word_tokens if not word in stop_words]
                word_counts = Counter(text)
            else: 
                word_counts = Counter(text.split())
    
            if self.stemming:        
                stemmer = nltk.PorterStemmer()
                stemmed_word_counts = Counter()
                
                for word, count in word_counts.items():
                    stemmed_word = stemmer.stem(word)                        
                    stemmed_word_counts[stemmed_word] += count
                    
                word_counts = stemmed_word_counts
                
            X_transformed.append(word_counts)
            
        return np.array(X_transformed)

class EmailToWordCounterTransformerPlusStopwords(BaseEstimator, TransformerMixin):

    def __init__(self, strip_headers=True, lower_case=True, remove_punctuation=True,
                 replace_urls=True, replace_numbers=True, remove_stopwords=True, stemming=True):
        self.strip_headers = strip_headers
        self.lower_case = lower_case
        self.remove_punctuation = remove_punctuation
        self.replace_urls = replace_urls
        self.replace_numbers = replace_numbers
        self.remove_stopwords = remove_stopwords
        self.stemming = stemming
        
    def fit(self, X, y=None):
        return self
    
    def transform(self, X, y=None):
        
        from collections import Counter
        import nltk
        from nltk.corpus import stopwords 
        from nltk.tokenize import word_tokenize
        import urlextract 
        import numpy as np
        
        X_transformed = []
        
        for email in X:
            text = email_to_text(email) or ""
            
            if self.lower_case:
                text = text.lower()
                
            if self.replace_urls:
                url_extractor = urlextract.URLExtract()
                urls = list(set(url_extractor.find_urls(text)))
                urls.sort(key=lambda url: len(url), reverse=True)
                for url in urls:
                    text = text.replace(url, " URL ")
                    
            if self.replace_numbers:
                text = re.sub(r'\d+(?:\.\d*(?:[eE]\d+))?', 'NUMBER', text)
                
            if self.remove_punctuation:
                text = re.sub(r'\W+', ' ', text, flags=re.M)
            
            if self.remove_stopwords:
                stop_words = set(stopwords.words("english"))
                word_tokens = word_tokenize(text)
                text = [word for word in word_tokens if not word in stop_words]
                word_counts = Counter(text)
            else: 
                word_counts = Counter(text.split())
    
            if self.stemming:        
                stemmer = nltk.PorterStemmer()
                stemmed_word_counts = Counter()
                
                for word, count in word_counts.items():
                    stemmed_word = stemmer.stem(word)                        
                    stemmed_word_counts[stemmed_word] += count
                    
                word_counts = stemmed_word_counts
                
            X_transformed.append(word_counts)
            
        return np.array(X_transformed)
    
from scipy.sparse import csr_matrix

class WordCounterToVectorTransformer(BaseEstimator, TransformerMixin):
    
    def __init__(self, vocabulary_size=1000):
        self.vocabulary_size = vocabulary_size
        
    def fit(self, X, y=None):
        
        from collections import Counter
        
        total_count = Counter()
        for word_count in X:
            for word, count in word_count.items():
                total_count[word] += min(count, 10)  # Why not += count?
                
        most_common = total_count.most_common()[:self.vocabulary_size]
        self.most_common_ = most_common
        self.vocabulary_ = {word: index + 1 for index, (word, count) in enumerate(most_common)}
        return self
    
    def transform(self, X, y=None):  
        
        rows = []
        cols = []
        data = []
        
        for row, word_count in enumerate(X):
            for word, count in word_count.items():
                rows.append(row)
                cols.append(self.vocabulary_.get(word, 0))
                data.append(count)
                
        return csr_matrix((data, (rows, cols)), shape=(len(X), self.vocabulary_size + 1))