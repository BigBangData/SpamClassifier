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