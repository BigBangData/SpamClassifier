import os
import re
import json
import nltk
import email
import tarfile
import requests
import urlextract 
import numpy as np
import email.policy
import scipy.sparse
import datetime as dt
    
from html import unescape
from collections import Counter
from nltk.corpus import stopwords 
from scipy.sparse import csr_matrix
from nltk.tokenize import word_tokenize
from sklearn.base import BaseEstimator, TransformerMixin

def get_data(spam, ham):
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
        uxtime = os.path.getmtime(os.path.join('data', emailtype))      
        return(dt.datetime.fromtimestamp(uxtime).strftime('%Y%m%d'))
    
    if (os.path.isdir(os.path.join('data', spam)) and get_date(spam) == date) \
    and (os.path.isdir(os.path.join('data', ham)) and get_date(ham) == date):
        print('Data successfully downloaded.')
    else: 
        _spam = ''.join([date, '_', spam])
        _ham = ''.join([date, '_', ham])
        get_data(_spam, _ham, date)
        
def extract_emails(_path, _names):

    def parse_emails(filename):
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
    structures = Counter()
    for email in emails:
        structure = get_structure(email)
        structures[structure] += 1
    return structures

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

    
class EmailToWordCounterTransformer_revised(BaseEstimator, TransformerMixin):

    def __init__(self, remove_stopwords, strip_headers=True, lower_case=True, remove_punctuation=True,
                 replace_urls=True, replace_numbers=True, stemming=True):
        self.remove_stopwords = remove_stopwords
        self.strip_headers = strip_headers
        self.lower_case = lower_case
        self.remove_punctuation = remove_punctuation
        self.replace_urls = replace_urls
        self.replace_numbers = replace_numbers
        self.stemming = stemming
    
    def fit(self, X, y=None):
        return self
    
    def transform(self, X, y=None):        
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


class WordCounterToVectorTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, vocabulary_size=1000):
        self.vocabulary_size = vocabulary_size
        
    def fit(self, X, y=None):
        total_count = Counter()
        for word_count in X:
            for word, count in word_count.items():
                total_count[word] += min(count, 10)
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
    
    
class WordCounterToVectorTransformer_plusvocab(BaseEstimator, TransformerMixin):
    def __init__(self, vocabulary_size=1000):
        self.vocabulary_size = vocabulary_size
        
    def fit(self, X, y=None):
        total_count = Counter()
        for word_count in X:
            for word, count in word_count.items():
                total_count[word] += min(count, 10)
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
      
        # CHANGE - needs vocabulary returned to save and run with test set
        return (self.vocabulary_, 
                csr_matrix((data, (rows, cols)), shape=(len(X), self.vocabulary_size + 1)))
    

def load_processed_X_train(vocab_name, X_train_name, preprocess_pipeline, X_train):
    
    # setup directory and file paths
    path = 'processed_data'
    if not os.path.exists(path):
        os.mkdir(path)       
    vocab_path = os.path.join(path, ''.join([vocab_name, '.json']))
    matrix_path = os.path.join(path, ''.join([X_train_name, '.npz']))
    
    # load vocabulary and matrix if exist
    try:
        with open(vocab_path, 'r') as fp:
            vocabulary_ = json.load(fp)
        print('Loading vocabulary.')
    except FileNotFoundError as e:  
        print('Json file not found.')
        pass
    try:
        X_train_transformed = scipy.sparse.load_npz(matrix_path)
        print('Loading sparse matrix.')
    except FileNotFoundError as e:  
        print('Sparse matrix not found.')
        pass
    
    if 'vocabulary_' in locals() and 'X_train_transformed' in locals():
        print('Processed data loaded.')
        return(vocabulary_, X_train_transformed)
    else:
        pass
    
    # if not, process data
    try:
        print('Processing data...')  
        vocabulary_, X_train_transformed = preprocess_pipeline.fit_transform(X_train)
        print('Data processed.')    
    except:
        print('Processing error.')
        pass
    
    # save processed data
    try:
        with open(vocab_path, 'w') as fp:
            json.dump(vocabulary_, fp, indent=4)
        print('Saving vocabulary...')
    except:
        print('Error saving vocabulary_...')
        pass
    try:
        scipy.sparse.save_npz(matrix_path, X_train_transformed)
        print('Saving sparse matrix...')
    except:
        print('Error saving matrix...')
    
    print('Processed data loaded and saved.')   
    return(vocabulary_, X_train_transformed)  
    
# -------------------------------------------------------------------------------------------------------------
# Studying scikit-learn TransformerMixin and BaseEstimator classes

# Adding TransformerMixin as a base class in our custom transformer ensures that all we need to do is write 
# our fit and transform methods and we get fit_transform for free.

# Adding BaseEstimator as a base class ensures we get get_params() and set_params() for free. 
# These are useful in hyperparameter tuning.

class TransformerMixin:
    """Mixin class for all transformers in scikit-learn."""

    def fit_transform(self, X, y=None, **fit_params):
        """
        Fit to data, then transform it.
        Fits transformer to X and y with optional parameters fit_params
        and returns a transformed version of X.
        Parameters
        ----------
        X : {array-like, sparse matrix, dataframe} of shape \
                (n_samples, n_features)
        y : ndarray of shape (n_samples,), default=None
            Target values.
        **fit_params : dict
            Additional fit parameters.
        Returns
        -------
        X_new : ndarray array of shape (n_samples, n_features_new)
            Transformed array.
        """
        # non-optimized default implementation; override when a better
        # method is possible for a given clustering algorithm
        if y is None:
            # fit method of arity 1 (unsupervised transformation)
            return self.fit(X, **fit_params).transform(X)
        else:
            # fit method of arity 2 (supervised transformation)
            return self.fit(X, y, **fit_params).transform(X)

        
class BaseEstimator:
    """Base class for all estimators in scikit-learn
    Notes
    -----
    All estimators should specify all the parameters that can be set
    at the class level in their ``__init__`` as explicit keyword
    arguments (no ``*args`` or ``**kwargs``).
    """

    @classmethod
    def _get_param_names(cls):
        """Get parameter names for the estimator"""
        # fetch the constructor or the original constructor before
        # deprecation wrapping if any
        init = getattr(cls.__init__, 'deprecated_original', cls.__init__)
        if init is object.__init__:
            # No explicit constructor to introspect
            return []

        # introspect the constructor arguments to find the model parameters
        # to represent
        init_signature = inspect.signature(init)
        # Consider the constructor parameters excluding 'self'
        parameters = [p for p in init_signature.parameters.values()
                      if p.name != 'self' and p.kind != p.VAR_KEYWORD]
        for p in parameters:
            if p.kind == p.VAR_POSITIONAL:
                raise RuntimeError("scikit-learn estimators should always "
                                   "specify their parameters in the signature"
                                   " of their __init__ (no varargs)."
                                   " %s with constructor %s doesn't "
                                   " follow this convention."
                                   % (cls, init_signature))
        # Extract and sort argument names excluding 'self'
        return sorted([p.name for p in parameters])

    def get_params(self, deep=True):
        """
        Get parameters for this estimator.
        Parameters
        ----------
        deep : bool, default=True
            If True, will return the parameters for this estimator and
            contained subobjects that are estimators.
        Returns
        -------
        params : mapping of string to any
            Parameter names mapped to their values.
        """
        out = dict()
        for key in self._get_param_names():
            try:
                value = getattr(self, key)
            except AttributeError:
                warnings.warn('From version 0.24, get_params will raise an '
                              'AttributeError if a parameter cannot be '
                              'retrieved as an instance attribute. Previously '
                              'it would return None.',
                              FutureWarning)
                value = None
            if deep and hasattr(value, 'get_params'):
                deep_items = value.get_params().items()
                out.update((key + '__' + k, val) for k, val in deep_items)
            out[key] = value
        return out

    def set_params(self, **params):
        """
        Set the parameters of this estimator.
        The method works on simple estimators as well as on nested objects
        (such as pipelines). The latter have parameters of the form
        ``<component>__<parameter>`` so that it's possible to update each
        component of a nested object.
        Parameters
        ----------
        **params : dict
            Estimator parameters.
        Returns
        -------
        self : object
            Estimator instance.
        """
        if not params:
            # Simple optimization to gain speed (inspect is slow)
            return self
        valid_params = self.get_params(deep=True)

        nested_params = defaultdict(dict)  # grouped by prefix
        for key, value in params.items():
            key, delim, sub_key = key.partition('__')
            if key not in valid_params:
                raise ValueError('Invalid parameter %s for estimator %s. '
                                 'Check the list of available parameters '
                                 'with `estimator.get_params().keys()`.' %
                                 (key, self))

            if delim:
                nested_params[key][sub_key] = value
            else:
                setattr(self, key, value)
                valid_params[key] = value

        for key, sub_params in nested_params.items():
            valid_params[key].set_params(**sub_params)

        return self

    def __repr__(self, N_CHAR_MAX=700):
        # N_CHAR_MAX is the (approximate) maximum number of non-blank
        # characters to render. We pass it as an optional parameter to ease
        # the tests.

        from .utils._pprint import _EstimatorPrettyPrinter

        N_MAX_ELEMENTS_TO_SHOW = 30  # number of elements to show in sequences

        # use ellipsis for sequences with a lot of elements
        pp = _EstimatorPrettyPrinter(
            compact=True, indent=1, indent_at_name=True,
            n_max_elements_to_show=N_MAX_ELEMENTS_TO_SHOW)

        repr_ = pp.pformat(self)

        # Use bruteforce ellipsis when there are a lot of non-blank characters
        n_nonblank = len(''.join(repr_.split()))
        if n_nonblank > N_CHAR_MAX:
            lim = N_CHAR_MAX // 2  # apprx number of chars to keep on both ends
            regex = r'^(\s*\S){%d}' % lim
            # The regex '^(\s*\S){%d}' % n
            # matches from the start of the string until the nth non-blank
            # character:
            # - ^ matches the start of string
            # - (pattern){n} matches n repetitions of pattern
            # - \s*\S matches a non-blank char following zero or more blanks
            left_lim = re.match(regex, repr_).end()
            right_lim = re.match(regex, repr_[::-1]).end()

            if '\n' in repr_[left_lim:-right_lim]:
                # The left side and right side aren't on the same line.
                # To avoid weird cuts, e.g.:
                # categoric...ore',
                # we need to start the right side with an appropriate newline
                # character so that it renders properly as:
                # categoric...
                # handle_unknown='ignore',
                # so we add [^\n]*\n which matches until the next \n
                regex += r'[^\n]*\n'
                right_lim = re.match(regex, repr_[::-1]).end()

            ellipsis = '...'
            if left_lim + len(ellipsis) < len(repr_) - right_lim:
                # Only add ellipsis if it results in a shorter repr
                repr_ = repr_[:left_lim] + '...' + repr_[-right_lim:]

        return repr_

    def __getstate__(self):
        try:
            state = super().__getstate__()
        except AttributeError:
            state = self.__dict__.copy()

        if type(self).__module__.startswith('sklearn.'):
            return dict(state.items(), _sklearn_version=__version__)
        else:
            return state

    def __setstate__(self, state):
        if type(self).__module__.startswith('sklearn.'):
            pickle_version = state.pop("_sklearn_version", "pre-0.18")
            if pickle_version != __version__:
                warnings.warn(
                    "Trying to unpickle estimator {0} from version {1} when "
                    "using version {2}. This might lead to breaking code or "
                    "invalid results. Use at your own risk.".format(
                        self.__class__.__name__, pickle_version, __version__),
                    UserWarning)
        try:
            super().__setstate__(state)
        except AttributeError:
            self.__dict__.update(state)

    def _more_tags(self):
        return _DEFAULT_TAGS

    def _get_tags(self):
        collected_tags = {}
        for base_class in reversed(inspect.getmro(self.__class__)):
            if hasattr(base_class, '_more_tags'):
                # need the if because mixins might not have _more_tags
                # but might do redundant work in estimators
                # (i.e. calling more tags on BaseEstimator multiple times)
                more_tags = base_class._more_tags(self)
                collected_tags.update(more_tags)
        return collected_tags

    def _check_n_features(self, X, reset):
        """Set the `n_features_in_` attribute, or check against it.
        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
            The input samples.
        reset : bool
            If True, the `n_features_in_` attribute is set to `X.shape[1]`.
            Else, the attribute must already exist and the function checks
            that it is equal to `X.shape[1]`.
        """
        n_features = X.shape[1]

        if reset:
            self.n_features_in_ = n_features
        else:
            if not hasattr(self, 'n_features_in_'):
                raise RuntimeError(
                    "The reset parameter is False but there is no "
                    "n_features_in_ attribute. Is this estimator fitted?"
                )
            if n_features != self.n_features_in_:
                raise ValueError(
                    'X has {} features, but this {} is expecting {} features '
                    'as input.'.format(n_features, self.__class__.__name__,
                                       self.n_features_in_)
                )

    def _validate_data(self, X, y=None, reset=True,
                       validate_separately=False, **check_params):
        """Validate input data and set or check the `n_features_in_` attribute.
        Parameters
        ----------
        X : {array-like, sparse matrix, dataframe} of shape \
                (n_samples, n_features)
            The input samples.
        y : array-like of shape (n_samples,), default=None
            The targets. If None, `check_array` is called on `X` and
            `check_X_y` is called otherwise.
        reset : bool, default=True
            Whether to reset the `n_features_in_` attribute.
            If False, the input will be checked for consistency with data
            provided when reset was last True.
        validate_separately : False or tuple of dicts, default=False
            Only used if y is not None.
            If False, call validate_X_y(). Else, it must be a tuple of kwargs
            to be used for calling check_array() on X and y respectively.
        **check_params : kwargs
            Parameters passed to :func:`sklearn.utils.check_array` or
            :func:`sklearn.utils.check_X_y`. Ignored if validate_separately
            is not False.
        Returns
        -------
        out : {ndarray, sparse matrix} or tuple of these
            The validated input. A tuple is returned if `y` is not None.
        """

        if y is None:
            if self._get_tags()['requires_y']:
                raise ValueError(
                    f"This {self.__class__.__name__} estimator "
                    f"requires y to be passed, but the target y is None."
                )
            X = check_array(X, **check_params)
            out = X
        else:
            if validate_separately:
                # We need this because some estimators validate X and y
                # separately, and in general, separately calling check_array()
                # on X and y isn't equivalent to just calling check_X_y()
                # :(
                check_X_params, check_y_params = validate_separately
                X = check_array(X, **check_X_params)
                y = check_array(y, **check_y_params)
            else:
                X, y = check_X_y(X, y, **check_params)
            out = X, y

        if check_params.get('ensure_2d', True):
            self._check_n_features(X, reset=reset)

        return out

    @property
    def _repr_html_(self):
        """HTML representation of estimator.
        This is redundant with the logic of `_repr_mimebundle_`. The latter
        should be favorted in the long term, `_repr_html_` is only
        implemented for consumers who do not interpret `_repr_mimbundle_`.
        """
        if get_config()["display"] != 'diagram':
            raise AttributeError("_repr_html_ is only defined when the "
                                 "'display' configuration option is set to "
                                 "'diagram'")
        return self._repr_html_inner

    def _repr_html_inner(self):
        """This function is returned by the @property `_repr_html_` to make
        `hasattr(estimator, "_repr_html_") return `True` or `False` depending
        on `get_config()["display"]`.
        """
        return estimator_html_repr(self)

    def _repr_mimebundle_(self, **kwargs):
        """Mime bundle used by jupyter kernels to display estimator"""
        output = {"text/plain": repr(self)}
        if get_config()["display"] == 'diagram':
            output["text/html"] = estimator_html_repr(self)
        return output