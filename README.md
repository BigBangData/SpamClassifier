# README

TODO:
1. explore technical details (ex. sparse matrix)

Saving the trained data as a pickled file or as a sparse matrix (scipy.sparse) makes it so that we lose the attributes of the trained data (self.vocabulary_ from WordCounterToVectorTransformer). Pickle has security issues and negative reviews overall, so will look into other methods (JSON...).

2. explore use case - is higher precision but lower recall preferred?
3. why removing stop words increases precision but lowers recall? Is this always so?
4. test other datasets
5. invite collaborators
6. make a nice presentation

random thought - recreate a classifier in R!
